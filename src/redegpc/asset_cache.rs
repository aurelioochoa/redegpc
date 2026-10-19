/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. https://mozilla.org/MPL/2.0/. */
//! Decode Derbh assets once on the host and serve an uncompressed archive.
//! The original IPA installation is never changed. Only the virtual filesystem's
//! read-only main.dz backing is redirected. No game or Apple code is patched.
//!
//! Format reference: https://dade.readthedocs.io/en/latest/api/marmalade.html
use super::hash::sha256;
use plist::{Dictionary, Value};
use std::fs::{self, File, OpenOptions};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::time::Instant;

const MAX_SOURCE: usize = 64 * 1024 * 1024;
const MAX_ENTRY: usize = 64 * 1024 * 1024;
const MAX_OUTPUT: usize = 256 * 1024 * 1024;
const MAX_HEADER: usize = 1024 * 1024;

extern "C" {
    fn redegpc_decode_lzma(
        input: *const u8,
        input_size: usize,
        output: *mut u8,
        output_size: usize,
        written: *mut usize,
    ) -> i32;
}

fn lzma(input: &[u8], expected: usize) -> Result<Vec<u8>, String> {
    if input.len() < 13 || expected > MAX_ENTRY {
        return Err("Invalid LZMA asset size".into());
    }
    let declared = u64::from_le_bytes(input[5..13].try_into().unwrap());
    if declared != u64::MAX && declared != expected as u64 {
        return Err("LZMA and archive sizes disagree".into());
    }
    // One spare byte detects oversized output, and lets empty streams finish.
    let mut output = vec![0; expected + 1];
    let mut written = 0;
    // The C decoder receives bounded, independent slices, never guest pointers.
    // Its dictionary allocations are bounded to 64 MiB as well.
    let result = unsafe {
        redegpc_decode_lzma(
            input.as_ptr(),
            input.len(),
            output.as_mut_ptr(),
            output.len(),
            &mut written,
        )
    };
    if result != 1 || written != expected {
        return Err(format!(
            "Invalid LZMA asset: status {result}, size {written}/{expected}"
        ));
    }
    output.truncate(expected);
    Ok(output)
}

fn u16_at(bytes: &[u8], offset: usize) -> Result<usize, String> {
    let bytes = bytes.get(offset..offset + 2).ok_or("Truncated archive")?;
    Ok(u16::from_le_bytes(bytes.try_into().unwrap()) as usize)
}
fn u32_at(bytes: &[u8], offset: usize) -> Result<usize, String> {
    let bytes = bytes.get(offset..offset + 4).ok_or("Truncated archive")?;
    Ok(u32::from_le_bytes(bytes.try_into().unwrap()) as usize)
}

/// Preserve names, attributes, ordering and every uncompressed asset byte.
/// Support the exact table layout in the qualified game; unfamiliar archives
/// deliberately fall back to the original loader instead of guessing.
fn expand(source: &[u8]) -> Result<Vec<u8>, String> {
    if source.len() > MAX_SOURCE || source.get(..4) != Some(b"DTRZ") {
        return Err("Unsupported game archive".into());
    }
    let files = u16_at(source, 4)?;
    let folders = u16_at(source, 6)?;
    if files == 0 || files > 4096 || folders == 0 || folders > 4096 || source.get(8) != Some(&0) {
        return Err("Invalid archive counts".into());
    }
    let mut position = 9;
    for _ in 0..files + folders - 1 {
        let rest = source
            .get(position..source.len().min(MAX_HEADER))
            .ok_or("Truncated archive names")?;
        let length = rest
            .iter()
            .position(|&b| b == 0)
            .ok_or("Unterminated archive name")?;
        if length == 0 {
            return Err("Empty archive name".into());
        }
        position += length + 1;
    }
    let mut seen = vec![false; files];
    for _ in 0..files {
        let folder = u16_at(source, position)?;
        let index = u16_at(source, position + 2)?;
        if folder >= folders || index >= files || seen[index] {
            return Err("Invalid archive file attributes".into());
        }
        seen[index] = true;
        position += 6;
    }
    if u16_at(source, position)? != 1 || u16_at(source, position + 2)? != files {
        return Err("Unsupported archive location table".into());
    }
    let table = position + 4;
    let header_end = table + files * 16;
    if header_end > source.len() || header_end > MAX_HEADER {
        return Err("Truncated archive locations".into());
    }
    let mut records = Vec::with_capacity(files);
    let mut total = header_end;
    for i in 0..files {
        let p = table + i * 16;
        let offset = u32_at(source, p)?;
        let size = u32_at(source, p + 4)?;
        let size2 = u32_at(source, p + 8)?;
        let method = u32_at(source, p + 12)?;
        if offset < header_end
            || offset >= source.len()
            || size != size2
            || size > MAX_ENTRY
            || ![0x100, 0x200].contains(&method)
        {
            return Err("Unsupported archive location or compression".into());
        }
        total = total
            .checked_add(size)
            .filter(|&n| n <= MAX_OUTPUT)
            .ok_or("Decoded archive exceeds limit")?;
        records.push((offset, size, method));
    }
    let mut offsets: Vec<_> = records.iter().map(|r| r.0).collect();
    offsets.sort_unstable();
    if offsets.windows(2).any(|pair| pair[0] == pair[1]) {
        return Err("Overlapping archive data offsets".into());
    }
    offsets.push(source.len());
    let mut output = Vec::with_capacity(total);
    output.extend_from_slice(&source[..header_end]);
    for (i, &(offset, size, method)) in records.iter().enumerate() {
        // Location records can be out of offset order. Window each compressed
        // stream by the next physical offset rather than by the next record.
        let index = offsets.binary_search(&offset).unwrap();
        let data = &source[offset..offsets[index + 1]];
        let decoded = if method == 0x200 {
            lzma(data, size)?
        } else {
            data.get(..size).ok_or("Truncated stored asset")?.to_vec()
        };
        let p = table + i * 16;
        // Preserve the reader flags. In this older SDK, 0x200 selects the
        // automatic stream detector, which also accepts uncompressed data;
        // newer Derbh format descriptions use different flag meanings.
        for (delta, value) in [(0, output.len()), (4, size), (8, size), (12, method)] {
            output[p + delta..p + delta + 4].copy_from_slice(&(value as u32).to_le_bytes());
        }
        output.extend_from_slice(&decoded);
    }
    Ok(output)
}

fn read_bounded(path: &Path, limit: usize) -> Result<Vec<u8>, String> {
    let metadata = fs::symlink_metadata(path).map_err(|e| e.to_string())?;
    if !metadata.is_file() || metadata.len() > limit as u64 {
        return Err(format!("Not a bounded regular file: {}", path.display()));
    }
    let mut bytes = Vec::new();
    File::open(path)
        .map_err(|e| e.to_string())?
        .take(limit as u64 + 1)
        .read_to_end(&mut bytes)
        .map_err(|e| e.to_string())?;
    if bytes.len() > limit {
        return Err("File grew beyond cache limit".into());
    }
    Ok(bytes)
}

fn atomic_bytes(path: &Path, bytes: &[u8]) -> Result<(), String> {
    let directory = path.parent().ok_or("Missing cache directory")?;
    let temporary = directory.join(format!(".assets-{}", uuid::Uuid::new_v4()));
    let result = (|| -> std::io::Result<()> {
        let mut file = OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&temporary)?;
        file.write_all(bytes)?;
        file.sync_all()?;
        fs::rename(&temporary, path)?;
        File::open(directory)?.sync_all()
    })();
    if result.is_err() {
        let _ = fs::remove_file(temporary);
    }
    result.map_err(|e| e.to_string())
}

pub(crate) fn prepare(source: &Path, cache: &Path) -> Result<PathBuf, String> {
    let started = Instant::now();
    let original = read_bounded(source, MAX_SOURCE)?;
    let source_hash = sha256(original.as_slice()).map_err(|e| e.to_string())?;
    let path = cache.join(format!("{source_hash}.dz"));
    let manifest_path = cache.join(format!("{source_hash}.plist"));
    let cached = (|| -> Option<()> {
        let manifest = read_bounded(&manifest_path, 4096).ok()?;
        let manifest = Value::from_reader(std::io::Cursor::new(manifest)).ok()?;
        let dict = manifest.as_dictionary()?;
        if dict.get("Version")?.as_unsigned_integer()? != 1
            || dict.get("SourceSHA256")?.as_string()? != source_hash
        {
            return None;
        }
        let bytes = read_bounded(&path, MAX_OUTPUT).ok()?;
        if sha256(bytes.as_slice()).ok()? != dict.get("DecodedSHA256")?.as_string()? {
            return None;
        }
        Some(())
    })();
    if cached.is_some() {
        log_dbg!(
            "Verified decoded asset cache in {:.3}s",
            started.elapsed().as_secs_f64()
        );
        return Ok(path);
    }
    let decoded = expand(&original)?;
    fs::create_dir_all(cache).map_err(|e| e.to_string())?;
    atomic_bytes(&path, &decoded)?;
    let mut manifest = Dictionary::new();
    manifest.insert("Version".into(), Value::Integer(1u64.into()));
    manifest.insert("SourceSHA256".into(), Value::String(source_hash));
    manifest.insert(
        "DecodedSHA256".into(),
        Value::String(sha256(decoded.as_slice()).map_err(|e| e.to_string())?),
    );
    super::import::write_plist_atomic(&manifest_path, &Value::Dictionary(manifest))?;
    log!(
        "Prepared decoded assets in {:.3}s; future level loads reuse the cache",
        started.elapsed().as_secs_f64()
    );
    Ok(path)
}

/// The shipped mobile profile requests a draw callback after each 10 KiB of
/// resource serialization. Each callback waits for the main run loop, turning
/// large loads into hundreds of frame waits. Batch that work while keeping
/// progress callbacks bounded to 50 ms.
pub(crate) fn prepare_config(source: &Path, cache: &Path) -> Result<PathBuf, String> {
    let mut bytes = read_bounded(source, MAX_HEADER)?;
    let source_hash = sha256(bytes.as_slice()).map_err(|e| e.to_string())?;
    bytes.extend_from_slice(
        b"\n{}\n[BIOHAZARD]\nSerialiseCallbackBytes=1048576\nSerialiseCallbackMs=50\n",
    );
    let path = cache.join(format!("{source_hash}-loading-v1.icf"));
    if read_bounded(&path, MAX_HEADER).is_ok_and(|cached| cached == bytes) {
        return Ok(path);
    }
    fs::create_dir_all(cache).map_err(|e| e.to_string())?;
    atomic_bytes(&path, &bytes)?;
    Ok(path)
}

#[cfg(test)]
mod tests {
    use super::*;
    const COMPRESSED: &[u8] = &[
        93, 0, 0, 128, 0, 255, 255, 255, 255, 255, 255, 255, 255, 0, 49, 152, 72, 153, 138, 182,
        200, 37, 2, 116, 251, 97, 216, 172, 59, 215, 182, 45, 181, 74, 236, 216, 175, 200, 4, 182,
        2, 159, 80, 232, 207, 225, 195, 30, 213, 49, 179, 19, 46, 60, 181, 182, 104, 214, 50, 152,
        115, 144, 249, 163, 184, 95, 255, 253, 10, 128, 0,
    ];
    fn payload() -> Vec<u8> {
        b"cached asset bytes\0".repeat(300)
    }
    fn archive() -> (Vec<u8>, usize) {
        let mut bytes = b"DTRZ\x02\0\x01\0\0first\0second\0".to_vec();
        for index in 0..2u16 {
            for value in [0, index, 0xffff] {
                bytes.extend_from_slice(&value.to_le_bytes());
            }
        }
        bytes.extend_from_slice(&[1, 0, 2, 0]);
        let table = bytes.len();
        bytes.resize(table + 32, 0);
        let first_offset = bytes.len();
        bytes.extend_from_slice(b"plain");
        let second_offset = bytes.len();
        bytes.extend_from_slice(COMPRESSED);
        // File records deliberately use the opposite physical data order.
        for (i, record) in [
            (second_offset, payload().len(), 0x200),
            (first_offset, 5, 0x100),
        ]
        .iter()
        .enumerate()
        {
            for (j, value) in [record.0, record.1, record.1, record.2].iter().enumerate() {
                bytes[table + i * 16 + j * 4..table + i * 16 + j * 4 + 4]
                    .copy_from_slice(&(*value as u32).to_le_bytes());
            }
        }
        (bytes, table)
    }

    #[test]
    fn decoded_archive_preserves_every_asset_with_unordered_locations() {
        let (source, table) = archive();
        let output = expand(&source).unwrap();
        assert_eq!(&output[..table], &source[..table]);
        let first = u32_at(&output, table).unwrap();
        let second = u32_at(&output, table + 16).unwrap();
        assert_eq!(&output[first..second], payload());
        assert_eq!(&output[second..], b"plain");
        assert_eq!(u32_at(&output, table + 12).unwrap(), 0x200);
        assert_eq!(u32_at(&output, table + 28).unwrap(), 0x100);
    }

    #[test]
    fn invalid_and_unbounded_archives_fall_back_without_panicking() {
        let (source, table) = archive();
        for length in 0..source.len() {
            assert!(expand(&source[..length]).is_err(), "prefix {length}");
        }
        for (offset, value) in [
            (table, 0),
            (table, usize::MAX as u32),
            (table + 4, (MAX_ENTRY + 1) as u32),
            (table + 8, 42),
            (table + 12, 0x999),
        ] {
            let mut bad = source.clone();
            bad[offset..offset + 4].copy_from_slice(&value.to_le_bytes());
            assert!(expand(&bad).is_err());
        }
        let mut bad = COMPRESSED.to_vec();
        bad[0] = 0xff;
        assert!(lzma(&bad, payload().len()).is_err());
        let mut oversized_dict = COMPRESSED.to_vec();
        oversized_dict[1..5].copy_from_slice(&u32::MAX.to_le_bytes());
        assert!(lzma(&oversized_dict, payload().len()).is_err());
        assert!(lzma(COMPRESSED, payload().len() - 1).is_err());
    }

    #[test]
    fn loading_profile_preserves_original_and_repairs_its_cached_copy() {
        let directory =
            std::env::temp_dir().join(format!("redegpc-config-test-{}", uuid::Uuid::new_v4()));
        fs::create_dir(&directory).unwrap();
        let source = directory.join("app.icf");
        let cache = directory.join("cache");
        let original = b"[BIOHAZARD]\nLanguage=IPHONE_ENGLISH\nSerialiseCallbackBytes=10240\n";
        fs::write(&source, original).unwrap();
        let path = prepare_config(&source, &cache).unwrap();
        let prepared = fs::read(&path).unwrap();
        assert!(prepared.starts_with(original));
        assert!(prepared.ends_with(b"SerialiseCallbackMs=50\n"));
        assert_eq!(fs::read(&source).unwrap(), original);
        fs::write(&path, b"partial").unwrap();
        assert_eq!(prepare_config(&source, &cache).unwrap(), path);
        assert_eq!(fs::read(&path).unwrap(), prepared);
        fs::remove_dir_all(directory).unwrap();
    }

    #[test]
    fn cache_reuses_valid_data_and_repairs_corruption_without_touching_source() {
        let directory =
            std::env::temp_dir().join(format!("redegpc-assets-test-{}", uuid::Uuid::new_v4()));
        fs::create_dir(&directory).unwrap();
        let source_path = directory.join("main.dz");
        let cache = directory.join("cache");
        let (source, _) = archive();
        fs::write(&source_path, &source).unwrap();
        let path = prepare(&source_path, &cache).unwrap();
        let expected = fs::read(&path).unwrap();
        let modified = fs::metadata(&path).unwrap().modified().unwrap();
        assert_eq!(prepare(&source_path, &cache).unwrap(), path);
        assert_eq!(fs::metadata(&path).unwrap().modified().unwrap(), modified);
        let mut corrupt = expected.clone();
        *corrupt.last_mut().unwrap() ^= 1;
        fs::write(&path, corrupt).unwrap();
        assert_eq!(prepare(&source_path, &cache).unwrap(), path);
        assert_eq!(fs::read(&path).unwrap(), expected);
        let manifest = path.with_extension("plist");
        fs::write(&manifest, b"interrupted write").unwrap();
        prepare(&source_path, &cache).unwrap();
        assert_eq!(fs::read(&source_path).unwrap(), source);
        let mut changed_source = source.clone();
        changed_source[9] = b'F';
        fs::write(&source_path, changed_source).unwrap();
        assert_ne!(prepare(&source_path, &cache).unwrap(), path);
        assert!(path.is_file());
        fs::remove_dir_all(directory).unwrap();
    }
}
