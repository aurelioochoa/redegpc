/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. https://mozilla.org/MPL/2.0/. */
//! Typed, cwd-independent entry to the inherited runtime.
use std::path::PathBuf;
use std::sync::OnceLock;

#[derive(Clone, Debug)]
pub struct GameSettings {
    pub fullscreen: bool,
    pub touch_mode: bool,
    /// Master volume, from 0 (muted) to 1.
    pub volume: f32,
    pub print_fps: bool,
}
impl Default for GameSettings {
    fn default() -> Self {
        Self {
            fullscreen: false,
            touch_mode: false,
            volume: 1.0,
            print_fps: false,
        }
    }
}

#[derive(Clone, Debug)]
pub struct RuntimeConfig {
    pub app_path: PathBuf,
    pub resource_directory: PathBuf,
    /// Saves live below this directory in touchHLE_sandbox/<bundle id>.
    pub data_directory: PathBuf,
    pub config_directory: PathBuf,
    pub log_directory: PathBuf,
    pub settings: GameSettings,
}

pub(crate) static CONFIG: OnceLock<RuntimeConfig> = OnceLock::new();
static DECODED_ARCHIVE: OnceLock<PathBuf> = OnceLock::new();
static LOADING_CONFIG: OnceLock<PathBuf> = OnceLock::new();

pub(crate) fn decoded_archive() -> Option<&'static std::path::Path> {
    DECODED_ARCHIVE.get().map(PathBuf::as_path)
}

pub(crate) fn loading_config() -> Option<&'static std::path::Path> {
    LOADING_CONFIG.get().map(PathBuf::as_path)
}

/// Hold an OS lease for the lifetime of the guest. A second runtime must not
/// snapshot the sandbox while the first one rotates save files at shutdown.
#[cfg(unix)]
struct RunLease(std::fs::File);
#[cfg(unix)]
impl RunLease {
    fn acquire(data: &std::path::Path) -> Result<Self, String> {
        use std::os::fd::AsRawFd;
        let file = std::fs::OpenOptions::new()
            .read(true)
            .write(true)
            .create(true)
            .truncate(false)
            .open(data.join("run.lock"))
            .map_err(|e| e.to_string())?;
        if unsafe { ::libc::flock(file.as_raw_fd(), ::libc::LOCK_EX | ::libc::LOCK_NB) } != 0 {
            return Err(format!(
                "Another redegpc runtime is using this save directory: {} ({})",
                data.display(),
                std::io::Error::last_os_error()
            ));
        }
        Ok(Self(file))
    }
}
#[cfg(unix)]
impl Drop for RunLease {
    fn drop(&mut self) {
        use std::os::fd::AsRawFd;
        unsafe {
            ::libc::flock(self.0.as_raw_fd(), ::libc::LOCK_UN);
        }
    }
}

/// Movie audio and OpenAL share the application's master gain.
pub fn volume() -> f32 {
    CONFIG.get().map_or(1.0, |c| c.settings.volume)
}

pub fn validate_resources(path: &std::path::Path) -> Result<(), String> {
    for file in [
        "touchHLE_default_options.txt",
        "touchHLE_dylibs/COPYING.libgcc",
        "touchHLE_dylibs/COPYING.libsqlite3",
        "touchHLE_dylibs/COPYING.libstdcxx",
        "touchHLE_dylibs/COPYING.libxml2",
        "touchHLE_dylibs/COPYING.libz",
        "touchHLE_dylibs/README.md",
        "touchHLE_dylibs/libgcc_s.1.dylib",
        "touchHLE_dylibs/libsqlite3.dylib",
        "touchHLE_dylibs/libstdc++.6.0.9.dylib",
        "touchHLE_dylibs/libxml2.2.dylib",
        "touchHLE_dylibs/libz.1.2.3.dylib",
        "touchHLE_fonts/LICENSE.liberation",
        "touchHLE_fonts/LICENSE.noto",
        "touchHLE_fonts/LiberationMono-Bold.ttf",
        "touchHLE_fonts/LiberationMono-BoldItalic.ttf",
        "touchHLE_fonts/LiberationMono-Italic.ttf",
        "touchHLE_fonts/LiberationMono-Regular.ttf",
        "touchHLE_fonts/LiberationSans-Bold.ttf",
        "touchHLE_fonts/LiberationSans-BoldItalic.ttf",
        "touchHLE_fonts/LiberationSans-Italic.ttf",
        "touchHLE_fonts/LiberationSans-Regular.ttf",
        "touchHLE_fonts/LiberationSerif-Bold.ttf",
        "touchHLE_fonts/LiberationSerif-BoldItalic.ttf",
        "touchHLE_fonts/LiberationSerif-Italic.ttf",
        "touchHLE_fonts/LiberationSerif-Regular.ttf",
        "touchHLE_fonts/NotoSansJP-Bold.otf",
        "touchHLE_fonts/NotoSansJP-Regular.otf",
        "touchHLE_fonts/README.md",
    ] {
        if !path.join(file).is_file() {
            return Err(format!(
                "Missing runtime resource {}",
                path.join(file).display()
            ));
        }
    }
    Ok(())
}

/// Runs one game per process, on the host's main thread. No cwd/env mutation.
pub fn run(mut config: RuntimeConfig) -> Result<(), String> {
    if !config.settings.volume.is_finite() || !(0.0..=1.0).contains(&config.settings.volume) {
        return Err("Volume must be between 0 and 1".into());
    }
    config.app_path = config.app_path.canonicalize().map_err(|e| e.to_string())?;
    config.resource_directory = config
        .resource_directory
        .canonicalize()
        .map_err(|e| e.to_string())?;
    validate_resources(&config.resource_directory)?;
    for path in [
        &mut config.data_directory,
        &mut config.config_directory,
        &mut config.log_directory,
    ] {
        std::fs::create_dir_all(&*path).map_err(|e| e.to_string())?;
        *path = path.canonicalize().map_err(|e| e.to_string())?;
    }
    let app = config.app_path.clone();
    let settings = config.settings.clone();
    #[cfg(unix)]
    let _lease = RunLease::acquire(&config.data_directory)?;
    CONFIG
        .set(config)
        .map_err(|_| "A runtime has already been initialized in this process")?;
    #[cfg(target_os = "linux")]
    if std::env::var_os("REDEGPC_ORIGINAL_ASSETS").is_none_or(|v| v != "1") {
        let config = CONFIG.get().unwrap();
        match super::asset_cache::prepare(
            &config.app_path.join("main.dz"),
            &config.data_directory.join("cache/assets-v1"),
        ) {
            Ok(path) => {
                let _ = DECODED_ARCHIVE.set(path);
            }
            Err(error) => {
                log!("Decoded asset cache unavailable, using original archive: {error}");
            }
        }
        match super::asset_cache::prepare_config(
            &config.app_path.join("app.icf"),
            &config.data_directory.join("cache/assets-v1"),
        ) {
            Ok(path) => {
                let _ = LOADING_CONFIG.set(path);
            }
            Err(error) => {
                log!("Loading profile unavailable, using original configuration: {error}");
            }
        }
    }
    let options = crate::options::Options::default();
    crate::launch_app(app, options, Vec::new(), None, false, Some(settings))
}

pub(crate) fn apply_settings(options: &mut crate::options::Options, settings: GameSettings) {
    options.fullscreen = settings.fullscreen;
    options.redegpc_controls = !settings.touch_mode;
    options.initial_orientation = crate::window::DeviceOrientation::LandscapeLeft;
    options.device_family = Some(crate::window::DeviceFamily::iPhone);
    options.scale_hack = std::num::NonZeroU32::new(1).unwrap();
    options.print_fps = settings.print_fps;
    // Airplay's loader waits on a semaphore posted from MainView's drawRect:.
    // The fullscreen CAEAGLLayer fast path skips display_layers and therefore
    // never delivers that callback. Baseline native/guest traces and a
    // --force-composition control run establish this per-game requirement.
    options.force_composition = true;
    options.popup_errors = false;
    options.preferred_languages = Some(vec!["en".into()]);
}

#[cfg(all(test, unix))]
mod tests {
    use super::*;
    #[test]
    fn runtime_lease_prevents_overlapping_save_rotation_and_releases() {
        let directory =
            std::env::temp_dir().join(format!("redegpc-lease-{}", uuid::Uuid::new_v4()));
        std::fs::create_dir(&directory).unwrap();
        let first = RunLease::acquire(&directory).unwrap();
        assert!(RunLease::acquire(&directory).is_err());
        drop(first);
        let next = RunLease::acquire(&directory).unwrap();
        drop(next);
        std::fs::remove_dir_all(directory).unwrap();
    }
}
