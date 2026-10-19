/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. https://mozilla.org/MPL/2.0/. */
//! Transactional IPA import. The current pointer is the only commit point.
use super::hash::sha256;
use plist::{Dictionary, Value};
use std::collections::{BTreeMap, HashSet};
use std::fs::{self, File, OpenOptions};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};

pub const BUNDLE_ID: &str = "jp.co.capcom.residentevil.en";
pub const VERSION: &str = "1.03.00";
const MAX_FILE: u64 = 512 * 1024 * 1024;
const MAX_TOTAL: u64 = 2 * 1024 * 1024 * 1024;

#[derive(Debug)]
pub struct Installation {
    pub root: PathBuf,
    pub app: PathBuf,
    pub ipa_sha256: String,
    pub files: usize,
}

fn error(e: impl std::fmt::Display) -> String {
    e.to_string()
}

fn dict(v: &Value) -> Result<&Dictionary, String> {
    v.as_dictionary()
        .ok_or_else(|| "Expected property-list dictionary".into())
}
fn string<'a>(d: &'a Dictionary, key: &str) -> Result<&'a str, String> {
    d.get(key)
        .and_then(Value::as_string)
        .ok_or_else(|| format!("Missing or invalid {key}"))
}
fn digest_ok(s: &str) -> bool {
    s.len() == 64
        && s.bytes()
            .all(|c| c.is_ascii_digit() || (b'a'..=b'f').contains(&c))
}
fn safe_path(name: &str) -> Result<PathBuf, String> {
    if name.is_empty() || name.contains(['\\', ':', '\0']) || name.starts_with('/') {
        return Err(format!("Unsafe archive path: {name:?}"));
    }
    let name = name.strip_suffix('/').unwrap_or(name);
    if name
        .split('/')
        .any(|c| c.is_empty() || c == "." || c == "..")
    {
        return Err(format!("Unsafe archive path: {name:?}"));
    }
    Ok(PathBuf::from(name))
}

struct Cleanup(PathBuf);
impl Drop for Cleanup {
    fn drop(&mut self) {
        if self.0.is_dir() {
            let _ = fs::remove_dir_all(&self.0);
        } else {
            let _ = fs::remove_file(&self.0);
        }
    }
}

pub(super) fn write_plist_atomic(path: &Path, value: &Value) -> Result<(), String> {
    let parent = path.parent().ok_or("Missing parent directory")?;
    fs::create_dir_all(parent).map_err(error)?;
    let temporary = parent.join(format!(".write-{}", uuid::Uuid::new_v4()));
    let _cleanup = Cleanup(temporary.clone());
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&temporary)
        .map_err(error)?;
    value.to_writer_xml(&mut file).map_err(error)?;
    file.sync_all().map_err(error)?;
    fs::rename(&temporary, path).map_err(error)?;
    sync_dir(parent)
}
fn sync_dir(path: &Path) -> Result<(), String> {
    File::open(path).and_then(|f| f.sync_all()).map_err(error)
}

/// Import a single supported IPA. Extraction and validation finish before commit.
pub fn import_ipa(ipa: &Path, data: &Path) -> Result<Installation, String> {
    fs::create_dir_all(data).map_err(error)?;
    let lock_path = data.join("import.lock");
    let mut lock = OpenOptions::new().write(true).create_new(true).open(&lock_path)
        .map_err(|e| format!("Cannot acquire {}: {e}. If an earlier import crashed, remove this lock after checking no importer is running.", lock_path.display()))?;
    let _lock = Cleanup(lock_path);
    writeln!(lock, "{}", std::process::id()).map_err(error)?;

    let mut input = File::open(ipa).map_err(|e| format!("Cannot open {}: {e}", ipa.display()))?;
    if input.metadata().map_err(error)?.len() > MAX_TOTAL {
        return Err("IPA exceeds 2 GiB limit".into());
    }
    let ipa_hash = sha256(&mut input).map_err(error)?;
    use std::io::Seek;
    input.rewind().map_err(error)?;
    let mut zip = zip::ZipArchive::new(input).map_err(|e| format!("Invalid IPA archive: {e}"))?;
    if zip.len() > 50_000 {
        return Err("Too many archive entries".into());
    }

    // Validate every path and mode before creating any extracted files.
    let mut seen = HashSet::new();
    let mut paths = Vec::new();
    let mut total = 0u64;
    let mut apps = HashSet::new();
    for i in 0..zip.len() {
        let mut entry = zip.by_index(i).map_err(error)?;
        let path = safe_path(entry.name())?;
        let canonical = path
            .to_str()
            .ok_or("Non-UTF-8 archive path")?
            .to_lowercase();
        if canonical == "manifest.plist" {
            return Err("Archive contains reserved manifest.plist".into());
        }
        if !seen.insert(canonical) {
            return Err(format!("Duplicate archive path: {:?}", entry.name()));
        }
        let is_link = entry
            .unix_mode()
            .is_some_and(|mode| mode & 0o170000 == 0o120000);
        if let Some(mode) = entry.unix_mode() {
            let kind = mode & 0o170000;
            if kind != 0 && kind != 0o100000 && kind != 0o040000 && !is_link {
                return Err(format!("Unsupported archive file type: {:?}", entry.name()));
            }
            if (kind == 0o040000) != entry.is_dir() && kind != 0 && kind != 0o100000 && !is_link {
                return Err("Archive type/path mismatch".into());
            }
        }
        total = total
            .checked_add(entry.size())
            .ok_or("Archive size overflow")?;
        if entry.size() > MAX_FILE || total > MAX_TOTAL {
            return Err("Archive exceeds extraction limits".into());
        }
        let parts: Vec<_> = entry.name().split('/').collect();
        if parts.len() == 3
            && parts[0] == "Payload"
            && parts[1].ends_with(".app")
            && parts[2] == "Info.plist"
        {
            apps.insert(format!("Payload/{}", parts[1]));
        }
        let link = if is_link {
            // Apple's standard signature alias is present in the supplied IPA.
            // Materialize that one exact file as a copy; never create a host
            // symlink, follow arbitrary targets, or permit symlink chains.
            let mut target = String::new();
            entry
                .by_ref()
                .take(4097)
                .read_to_string(&mut target)
                .map_err(error)?;
            if path.file_name().is_none_or(|n| n != "CodeResources")
                || target != "_CodeSignature/CodeResources"
            {
                return Err("Unsupported archive file type or unsafe symlink target".into());
            }
            Some(target)
        } else {
            None
        };
        paths.push((path, entry.is_dir(), entry.size(), link));
    }
    if apps.len() != 1 {
        return Err("IPA must contain exactly one Payload/*.app/Info.plist".into());
    }
    let app_relative = apps.into_iter().next().unwrap();
    let mut archive_links = Dictionary::new();
    for (path, _, _, target) in &paths {
        if let Some(target) = target {
            if path != &PathBuf::from(format!("{app_relative}/CodeResources")) {
                return Err("Signature alias must be at the app bundle root".into());
            }
            let target_name = format!("{app_relative}/{target}");
            let target_entry = zip.by_name(&target_name).map_err(error)?;
            if target_entry.is_dir()
                || target_entry
                    .unix_mode()
                    .is_some_and(|m| ![0, 0o100000].contains(&(m & 0o170000)))
            {
                return Err("Signature alias target must be a regular archive file".into());
            }
            total = total
                .checked_add(target_entry.size())
                .ok_or("Archive size overflow")?;
            if total > MAX_TOTAL {
                return Err("Archive exceeds extraction limits".into());
            }
            archive_links.insert(path.to_str().unwrap().into(), Value::String(target.clone()));
        }
    }
    let installations = data.join("installations");
    fs::create_dir_all(&installations).map_err(error)?;
    let stage = installations.join(format!(".import-{}", uuid::Uuid::new_v4()));
    fs::create_dir(&stage).map_err(error)?;
    let _stage = Cleanup(stage.clone());
    let mut hashes = Dictionary::new();
    for (i, (path, is_dir, expected_size, link)) in paths.iter().enumerate() {
        let destination = stage.join(path);
        if *is_dir {
            fs::create_dir_all(&destination).map_err(error)?;
            continue;
        }
        fs::create_dir_all(destination.parent().unwrap()).map_err(error)?;
        let mut file = OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&destination)
            .map_err(error)?;
        let mut entry = if let Some(target) = link {
            zip.by_name(&format!("{app_relative}/{target}"))
                .map_err(error)?
        } else {
            zip.by_index(i).map_err(error)?
        };
        let expected_size = if link.is_some() {
            entry.size()
        } else {
            *expected_size
        };
        let count =
            std::io::copy(&mut entry.by_ref().take(MAX_FILE + 1), &mut file).map_err(error)?;
        if count != expected_size || count > MAX_FILE {
            return Err("Archive entry size mismatch".into());
        }
        file.sync_all().map_err(error)?;
        hashes.insert(
            path.to_str().unwrap().into(),
            Value::String(sha256(File::open(&destination).map_err(error)?).map_err(error)?),
        );
    }
    validate_app(&stage.join(&app_relative))?;
    let mut manifest = Dictionary::new();
    manifest.insert("FormatVersion".into(), Value::Integer(1.into()));
    manifest.insert("BundleIdentifier".into(), Value::String(BUNDLE_ID.into()));
    manifest.insert("BundleVersion".into(), Value::String(VERSION.into()));
    manifest.insert("AppPath".into(), Value::String(app_relative));
    manifest.insert("IPASHA256".into(), Value::String(ipa_hash.clone()));
    manifest.insert("FilesSHA256".into(), Value::Dictionary(hashes));
    manifest.insert(
        "MaterializedArchiveLinks".into(),
        Value::Dictionary(archive_links),
    );
    write_plist_atomic(&stage.join("manifest.plist"), &Value::Dictionary(manifest))?;
    // Verify the exact staged artifact before either installation or pointer
    // can become visible. All fallible content checks precede commit.
    check_root(&stage, &ipa_hash)?;
    let mut source = zip.into_inner();
    source.rewind().map_err(error)?;
    if sha256(source).map_err(error)? != ipa_hash {
        return Err("Source IPA changed during import".into());
    }
    let destination = installations.join(&ipa_hash);
    if destination.exists() {
        check_root(&destination, &ipa_hash)?;
    } else {
        sync_tree(&stage)?;
        fs::rename(&stage, &destination).map_err(error)?;
        sync_dir(&installations)?;
    }
    let installation = check_root(&destination, &ipa_hash)?;
    let mut pointer = Dictionary::new();
    pointer.insert("Installation".into(), Value::String(ipa_hash.clone()));
    write_plist_atomic(&data.join("current.plist"), &Value::Dictionary(pointer))?;
    Ok(installation)
}

fn sync_tree(path: &Path) -> Result<(), String> {
    for e in fs::read_dir(path).map_err(error)? {
        let e = e.map_err(error)?;
        if e.file_type().map_err(error)?.is_dir() {
            sync_tree(&e.path())?;
        }
    }
    sync_dir(path)
}

fn validate_app(app: &Path) -> Result<(), String> {
    let info = Value::from_file(app.join("Info.plist")).map_err(error)?;
    let d = dict(&info)?;
    if string(d, "CFBundleIdentifier")? != BUNDLE_ID || string(d, "CFBundleVersion")? != VERSION {
        return Err(format!(
            "Unsupported game: expected English {BUNDLE_ID} v{VERSION}"
        ));
    }
    let executable = string(d, "CFBundleExecutable")?;
    let path = safe_path(executable)?;
    if path.components().count() != 1 {
        return Err("Executable must be a bundle file name".into());
    }
    validate_macho(&fs::read(app.join(path)).map_err(error)?)?;
    for name in ["main.dz", "intro.mp4"] {
        if !app.join(name).is_file() {
            return Err(format!("Missing game resource: {name}"));
        }
    }
    Ok(())
}

fn validate_macho(bytes: &[u8]) -> Result<(), String> {
    fn word(bytes: &[u8], offset: usize) -> Result<u32, String> {
        Ok(u32::from_le_bytes(
            bytes
                .get(offset..offset + 4)
                .ok_or("Truncated Mach-O")?
                .try_into()
                .unwrap(),
        ))
    }
    if word(bytes, 0)? != 0xfeedface || word(bytes, 4)? != 12 || word(bytes, 12)? != 2 {
        return Err(
            "Unsupported executable: expected little-endian 32-bit ARM Mach-O executable".into(),
        );
    }
    let subtype = word(bytes, 8)? & 0x00ffffff;
    if ![0, 6, 9, 11].contains(&subtype) {
        return Err(format!("Unsupported ARM subtype {subtype}"));
    }
    let count = word(bytes, 16)? as usize;
    let command_end = 28usize
        .checked_add(word(bytes, 20)? as usize)
        .ok_or("Invalid Mach-O size")?;
    if command_end > bytes.len() || count > 8192 {
        return Err("Truncated Mach-O commands".into());
    }
    let mut offset = 28;
    for _ in 0..count {
        let cmd = word(bytes, offset)?;
        let size = word(bytes, offset + 4)? as usize;
        let end = offset
            .checked_add(size)
            .ok_or("Invalid Mach-O command size")?;
        if size < 8 || !size.is_multiple_of(4) || end > command_end {
            return Err("Invalid Mach-O command bounds".into());
        }
        if cmd == 0x21 {
            if size < 20 {
                return Err("Truncated encryption command".into());
            }
            if word(bytes, offset + 16)? != 0 {
                return Err("Encrypted executable: a decrypted IPA is required".into());
            }
        }
        offset = end;
    }
    if offset != command_end {
        return Err("Mach-O command table length mismatch".into());
    }
    Ok(())
}

pub fn check(data: &Path) -> Result<Installation, String> {
    let pointer = Value::from_file(data.join("current.plist")).map_err(|e| {
        format!("No readable imported installation ({e}). Run: redegpc import \"game.ipa\"")
    })?;
    let hash = string(dict(&pointer)?, "Installation")?;
    if !digest_ok(hash) {
        return Err("Invalid installation identifier".into());
    }
    check_root(&data.join("installations").join(hash), hash)
}

fn regular_tree(
    root: &Path,
    path: &Path,
    files: &mut BTreeMap<String, PathBuf>,
) -> Result<(), String> {
    let meta = fs::symlink_metadata(path).map_err(error)?;
    if meta.file_type().is_symlink() {
        return Err(format!("Symlink in installation: {}", path.display()));
    }
    if meta.is_dir() {
        for entry in fs::read_dir(path).map_err(error)? {
            regular_tree(root, &entry.map_err(error)?.path(), files)?;
        }
    } else if meta.is_file() {
        files.insert(
            path.strip_prefix(root)
                .unwrap()
                .to_str()
                .ok_or("Non-UTF-8 installation path")?
                .into(),
            path.into(),
        );
    } else {
        return Err("Unsupported installation file type".into());
    }
    Ok(())
}

fn check_root(root: &Path, expected_hash: &str) -> Result<Installation, String> {
    let mut actual = BTreeMap::new();
    regular_tree(root, root, &mut actual)?;
    let manifest = Value::from_file(root.join("manifest.plist")).map_err(error)?;
    let d = dict(&manifest)?;
    if d.get("FormatVersion").and_then(Value::as_unsigned_integer) != Some(1)
        || string(d, "BundleIdentifier")? != BUNDLE_ID
        || string(d, "BundleVersion")? != VERSION
        || string(d, "IPASHA256")? != expected_hash
    {
        return Err("Unsupported or inconsistent installation manifest".into());
    }
    let app_relative = string(d, "AppPath")?;
    let relative = safe_path(app_relative)?;
    if relative.components().count() != 2
        || !app_relative.starts_with("Payload/")
        || !app_relative.ends_with(".app")
    {
        return Err("Invalid installed app path".into());
    }
    let hashes = dict(d.get("FilesSHA256").ok_or("Missing file hashes")?)?;
    actual.remove("manifest.plist");
    if actual.len() != hashes.len() {
        return Err("Installation file set differs from manifest".into());
    }
    for (name, value) in hashes {
        safe_path(name)?;
        let hash = value
            .as_string()
            .filter(|s| digest_ok(s))
            .ok_or("Invalid file hash")?;
        let path = actual
            .get(name)
            .ok_or_else(|| format!("Missing installed file: {name}"))?;
        if sha256(File::open(path).map_err(error)?).map_err(error)? != hash {
            return Err(format!("Installed file hash mismatch: {name}"));
        }
    }
    validate_app(&root.join(&relative))?;
    Ok(Installation {
        root: root.into(),
        app: root.join(relative),
        ipa_sha256: expected_hash.into(),
        files: hashes.len(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use zip::write::FileOptions;
    struct Fixture(PathBuf);
    impl Fixture {
        fn new() -> Self {
            let p = std::env::temp_dir().join(format!("redegpc-test-{}", uuid::Uuid::new_v4()));
            fs::create_dir(&p).unwrap();
            Self(p)
        }
        fn ipa(
            &self,
            name: &str,
            version: &str,
            encrypted: bool,
            extra: Option<(&str, &[u8])>,
        ) -> PathBuf {
            let p = self.0.join(name);
            let mut z = zip::ZipWriter::new(File::create(&p).unwrap());
            let mut d = Dictionary::new();
            for (k, v) in [
                ("CFBundleIdentifier", BUNDLE_ID),
                ("CFBundleVersion", version),
                ("CFBundleExecutable", "game"),
            ] {
                d.insert(k.into(), Value::String(v.into()));
            }
            let mut info = Vec::new();
            Value::Dictionary(d).to_writer_xml(&mut info).unwrap();
            let mut exe = Vec::new();
            for word in [
                0xfeedfaceu32,
                12,
                6,
                2,
                1,
                20,
                0,
                0x21,
                20,
                0,
                0,
                u32::from(encrypted),
            ] {
                exe.extend(word.to_le_bytes());
            }
            let entries = [
                ("Payload/game.app/Info.plist", info.as_slice()),
                ("Payload/game.app/game", exe.as_slice()),
                ("Payload/game.app/main.dz", b"original archive"),
                ("Payload/game.app/intro.mp4", b"movie"),
                ("Payload/game.app/config.ini", b"original config"),
            ];
            for (n, b) in entries.into_iter().chain(extra) {
                z.start_file(n, FileOptions::default()).unwrap();
                z.write_all(b).unwrap();
            }
            z.finish().unwrap();
            p
        }
    }
    impl Drop for Fixture {
        fn drop(&mut self) {
            let _ = fs::remove_dir_all(&self.0);
        }
    }
    #[test]
    fn import_atomic_rejections_and_source_independence() {
        let f = Fixture::new();
        let data = f.0.join("data");
        let good = f.ipa("good.ipa", VERSION, false, None);
        let installation = import_ipa(&good, &data).unwrap();
        assert_eq!(
            fs::read(installation.app.join("main.dz")).unwrap(),
            b"original archive"
        );
        assert_eq!(
            fs::read(installation.app.join("config.ini")).unwrap(),
            b"original config"
        );
        let saves = data.join("touchHLE_sandbox/progress");
        fs::create_dir_all(saves.parent().unwrap()).unwrap();
        fs::write(&saves, b"save").unwrap();
        let pointer = fs::read(data.join("current.plist")).unwrap();
        let corrupt = f.0.join("corrupt.ipa");
        fs::write(&corrupt, b"not zip").unwrap();
        let bad = [
            corrupt,
            f.ipa("unsafe.ipa", VERSION, false, Some(("../escape", b"bad"))),
            f.ipa("encrypted.ipa", VERSION, true, None),
            f.ipa("unsupported.ipa", "1.00.00", false, None),
            f.ipa(
                "duplicate.ipa",
                VERSION,
                false,
                Some(("Payload/game.app/main.dz", b"changed")),
            ),
            f.ipa(
                "manifest.ipa",
                VERSION,
                false,
                Some(("manifest.plist", b"bad")),
            ),
        ];
        for bad in bad {
            assert!(import_ipa(&bad, &data).is_err(), "{}", bad.display());
            assert_eq!(fs::read(data.join("current.plist")).unwrap(), pointer);
            assert_eq!(fs::read(&saves).unwrap(), b"save");
            check(&data).unwrap();
        }
        assert!(!f.0.join("escape").exists());
        assert!(fs::read_dir(data.join("installations")).unwrap().all(|e| !e
            .unwrap()
            .file_name()
            .to_str()
            .unwrap()
            .starts_with(".import-")));
        import_ipa(&good, &data).unwrap();
        fs::remove_file(good).unwrap();
        check(&data).unwrap();
        fs::write(installation.app.join("main.dz"), b"tampered").unwrap();
        assert!(check(&data).unwrap_err().contains("hash mismatch"));
    }
    #[test]
    fn malformed_macho_and_paths() {
        for path in ["/abs", "a/../b", "a/./b", "a//b", "C:/b", "a\\b", ""] {
            assert!(safe_path(path).is_err());
        }
        for n in 0..48 {
            assert!(validate_macho(&vec![0; n]).is_err());
        }
        let mut b = Vec::new();
        for w in [0xfeedfaceu32, 12, 6, 2, 1, 8, 0, 0x21, 8] {
            b.extend(w.to_le_bytes());
        }
        assert!(validate_macho(&b).is_err());
    }
    #[cfg(unix)]
    #[test]
    fn materializes_only_the_standard_signature_alias() {
        let f = Fixture::new();
        let p = f.ipa("signed.ipa", VERSION, false, None);
        let file = OpenOptions::new().read(true).write(true).open(&p).unwrap();
        let mut zip = zip::ZipWriter::new_append(file).unwrap();
        zip.start_file(
            "Payload/game.app/_CodeSignature/CodeResources",
            zip::write::FileOptions::default(),
        )
        .unwrap();
        zip.write_all(b"original signature bytes").unwrap();
        zip.add_symlink(
            "Payload/game.app/CodeResources",
            "_CodeSignature/CodeResources",
            zip::write::FileOptions::default(),
        )
        .unwrap();
        zip.finish().unwrap();
        let installation = import_ipa(&p, &f.0.join("data")).unwrap();
        let alias = installation.app.join("CodeResources");
        assert!(!fs::symlink_metadata(&alias)
            .unwrap()
            .file_type()
            .is_symlink());
        assert_eq!(fs::read(alias).unwrap(), b"original signature bytes");
        check(&f.0.join("data")).unwrap();
    }
    #[cfg(unix)]
    #[test]
    fn rejects_symlink_and_crc_corruption() {
        let f = Fixture::new();
        let data = f.0.join("data");
        let good = f.ipa("good.ipa", VERSION, false, None);
        let install = import_ipa(&good, &data).unwrap();
        let binary = install.app.join("game");
        fs::remove_file(&binary).unwrap();
        std::os::unix::fs::symlink("/etc/passwd", &binary).unwrap();
        assert!(check(&data).unwrap_err().contains("Symlink"));
        let p = f.0.join("link.ipa");
        let mut z = zip::ZipWriter::new(File::create(&p).unwrap());
        z.add_symlink("Payload/game.app/escape", "/tmp", FileOptions::default())
            .unwrap();
        z.finish().unwrap();
        assert!(import_ipa(&p, &data).unwrap_err().contains("file type"));
        let p = f.ipa("crc.ipa", VERSION, false, None);
        let mut bytes = fs::read(&p).unwrap();
        let at = {
            let mut zip = zip::ZipArchive::new(File::open(&p).unwrap()).unwrap();
            let entry = zip.by_name("Payload/game.app/main.dz").unwrap();
            entry.data_start() as usize
        };
        bytes[at] ^= 1;
        fs::write(&p, bytes).unwrap();
        assert!(import_ipa(&p, &data).is_err());
    }
}
