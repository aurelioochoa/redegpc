/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. https://mozilla.org/MPL/2.0/. */
//! Game-specific host application. Guest compatibility modules stay upstream.
#[cfg(target_os = "linux")]
pub(crate) mod asset_cache;
mod hash;
pub(crate) mod hud;
pub mod import;
pub(crate) mod metrics;
pub mod runtime;

use plist::{Dictionary, Value};
use runtime::{GameSettings, RuntimeConfig};
use std::ffi::OsString;
use std::path::{Path, PathBuf};

const HELP: &str = "redegpc — Resident Evil Degeneration for Linux x86_64

Usage:
  redegpc import <game.ipa>   Safely import English v1.03.00
  redegpc check               Verify installed executable and resource hashes
  redegpc run [options]       Launch the imported game
  redegpc launcher            Open the native incident dossier launcher
  redegpc                    Launch, or show import instructions
  redegpc --help
  redegpc --copyright         Runtime and dependency license notices

Run options (persisted after validation):
  --fullscreen | --windowed
  --volume=0..100
  --touch | --desktop
  --fps                      Print measured frame rates
  --resources <directory>    Override the bundled runtime resources

Controls: WASD/arrows move; right mouse aims; left mouse fires while aiming
and clicks menus; R reloads; E interacts; Tab inventory; Escape pause/back.
F11 toggles fullscreen. Touch mode preserves the original mouse/touch input.
Desktop action coordinates are being qualified against this exact game.

Data: $XDG_DATA_HOME/redegpc (default ~/.local/share/redegpc)
Settings: $XDG_CONFIG_HOME/redegpc (default ~/.config/redegpc)
Logs: $XDG_STATE_HOME/redegpc/logs (default ~/.local/state/redegpc/logs)
No game assets are bundled. Import copies the IPA contents; the source drive
is not needed afterwards.";

#[derive(Debug, Clone)]
pub struct Directories {
    pub data: PathBuf,
    pub config: PathBuf,
    pub logs: PathBuf,
}
impl Directories {
    pub fn discover() -> Result<Self, String> {
        let home = std::env::var_os("HOME")
            .filter(|v| !v.is_empty())
            .map(PathBuf::from)
            .ok_or("HOME must be set to resolve XDG directories")?;
        if !home.is_absolute() {
            return Err("HOME must be absolute".into());
        }
        let base = |key: &str, default: &str| {
            std::env::var_os(key)
                .map(PathBuf::from)
                .filter(|p| p.is_absolute())
                .unwrap_or_else(|| home.join(default))
                .join("redegpc")
        };
        Ok(Self {
            data: base("XDG_DATA_HOME", ".local/share"),
            config: base("XDG_CONFIG_HOME", ".config"),
            logs: base("XDG_STATE_HOME", ".local/state").join("logs"),
        })
    }
}

/// Executable-relative installed resources first; a source checkout is a
/// development fallback compiled into this particular binary.
fn resources() -> Result<PathBuf, String> {
    let exe = std::env::current_exe().map_err(|e| e.to_string())?;
    let parent = exe.parent().ok_or("Executable has no parent")?;
    for path in [
        parent.join("resources"),
        parent.join("../share/redegpc"),
        PathBuf::from(env!("CARGO_MANIFEST_DIR")),
    ] {
        if runtime::validate_resources(&path).is_ok() {
            return path.canonicalize().map_err(|e| e.to_string());
        }
    }
    Err(
        "Runtime resources were not found beside the executable. Use --resources <directory>."
            .into(),
    )
}

fn load_settings(config: &Path) -> Result<GameSettings, String> {
    let path = config.join("settings.plist");
    if !path.exists() {
        return Ok(GameSettings::default());
    }
    let v = Value::from_file(&path).map_err(|e| format!("Invalid {}: {e}", path.display()))?;
    let d = v
        .as_dictionary()
        .ok_or("Settings must be a property-list dictionary")?;
    let mut s = GameSettings::default();
    for (key, value) in d {
        match key.as_str() {
            "Fullscreen" => {
                s.fullscreen = value.as_boolean().ok_or("Invalid Fullscreen setting")?
            }
            "TouchMode" => s.touch_mode = value.as_boolean().ok_or("Invalid TouchMode setting")?,
            "Volume" => {
                s.volume = value
                    .as_real()
                    .filter(|v| v.is_finite() && (0.0..=1.0).contains(v))
                    .ok_or("Invalid Volume setting")? as f32
            }
            _ => return Err(format!("Unknown game setting: {key}")),
        }
    }
    Ok(s)
}
fn save_settings(config: &Path, s: &GameSettings) -> Result<(), String> {
    let mut d = Dictionary::new();
    d.insert("Fullscreen".into(), Value::Boolean(s.fullscreen));
    d.insert("TouchMode".into(), Value::Boolean(s.touch_mode));
    d.insert("Volume".into(), Value::Real(s.volume as f64));
    import::write_plist_atomic(&config.join("settings.plist"), &Value::Dictionary(d))
}

fn launcher() -> Result<(), String> {
    let exe = std::env::current_exe().map_err(|e| e.to_string())?;
    let parent = exe.parent().ok_or("Executable has no parent")?;
    let script = [
        parent.join("launcher/main.py"),
        parent.join("../share/redegpc/launcher/main.py"),
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("launcher/main.py"),
    ]
    .into_iter()
    .find(|p| p.is_file())
    .ok_or("Launcher resources were not found. Install the launcher directory beside the executable or under share/redegpc.")?;
    let status = std::process::Command::new("python3")
        .arg(script)
        .arg("--binary")
        .arg(exe)
        .status()
        .map_err(|e| {
            format!("Cannot start Python launcher: {e}. Install Python 3, Tk and Pillow.")
        })?;
    if status.success() {
        Ok(())
    } else {
        Err(format!("Launcher exited with {status}"))
    }
}

pub fn cli(args: impl IntoIterator<Item = OsString>) -> Result<(), String> {
    let mut args: Vec<_> = args.into_iter().collect();
    if args
        .first()
        .is_some_and(|a| a == "--help" || a == "-h" || a == "help")
    {
        if args.len() != 1 {
            return Err("--help takes no arguments".into());
        }
        println!("{HELP}");
        return Ok(());
    }
    if args.first().is_some_and(|a| a == "--copyright") {
        if args.len() != 1 {
            return Err("--copyright takes no arguments".into());
        }
        println!("{}", crate::licenses::get_text());
        return Ok(());
    }
    let command = if args.is_empty() {
        OsString::from("run")
    } else {
        args.remove(0)
    };
    if command == "launcher" {
        if !args.is_empty() {
            return Err("Usage: redegpc launcher".into());
        }
        return launcher();
    }
    let dirs = Directories::discover()?;
    if command == "import" {
        if args.len() != 1 {
            return Err("Usage: redegpc import <game.ipa>".into());
        }
        let installed = import::import_ipa(Path::new(&args[0]), &dirs.data)?;
        println!(
            "Imported English v{}: {} files\nIPA SHA-256: {}\nApp: {}",
            import::VERSION,
            installed.files,
            installed.ipa_sha256,
            installed.app.display()
        );
    } else if command == "check" {
        if !args.is_empty() {
            return Err("Usage: redegpc check".into());
        }
        let installed = import::check(&dirs.data)?;
        let resources = resources()?;
        runtime::validate_resources(&resources)?;
        println!("Installation verified: {} files, English v{}\nIPA SHA-256: {}\nResources: {}\nSaves: {}\nLogs: {}",installed.files,import::VERSION,installed.ipa_sha256,resources.display(),dirs.data.join("touchHLE_sandbox").display(),dirs.logs.display());
    } else if command == "run" {
        let mut s = load_settings(&dirs.config)?;
        let mut resource_override = None;
        let mut iter = args.into_iter();
        while let Some(arg) = iter.next() {
            match arg.to_str() {
                Some("--fullscreen") => s.fullscreen = true,
                Some("--windowed") => s.fullscreen = false,
                Some("--touch") => s.touch_mode = true,
                Some("--desktop") => s.touch_mode = false,
                Some("--fps") => s.print_fps = true,
                Some("--resources") => {
                    resource_override = Some(PathBuf::from(
                        iter.next().ok_or("--resources needs a directory")?,
                    ))
                }
                Some(v) if v.starts_with("--volume=") => {
                    let value: f32 = v[9..]
                        .parse()
                        .map_err(|_| "Invalid volume: expected 0..100")?;
                    if !value.is_finite() || !(0.0..=100.0).contains(&value) {
                        return Err("Invalid volume: expected 0..100".into());
                    }
                    s.volume = value / 100.0;
                }
                _ => return Err(format!("Unknown run option: {arg:?}. See redegpc --help")),
            }
        }
        let installation = import::check(&dirs.data)?;
        let resources = match resource_override {
            Some(path) => path,
            None => resources()?,
        };
        runtime::validate_resources(&resources)?;
        save_settings(&dirs.config, &s)?;
        // Keep upstream app options separate from our typed game settings.
        let upstream_options = dirs.config.join("touchHLE_options.txt");
        if !upstream_options.exists() {
            std::fs::write(
                &upstream_options,
                "# Additional touchHLE options; see OPTIONS_HELP.txt in the source tree.\n",
            )
            .map_err(|e| e.to_string())?;
        }
        println!(
            "Launching English v{}; log: {}",
            import::VERSION,
            dirs.logs.join("redegpc.log").display()
        );
        runtime::run(RuntimeConfig {
            app_path: installation.app,
            resource_directory: resources,
            data_directory: dirs.data,
            config_directory: dirs.config,
            log_directory: dirs.logs,
            settings: s,
        })?;
    } else {
        return Err(format!("Unknown command: {command:?}. See redegpc --help"));
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn settings_round_trip_and_rejection() {
        let p = std::env::temp_dir().join(format!("redegpc-settings-{}", uuid::Uuid::new_v4()));
        let settings = GameSettings {
            fullscreen: true,
            touch_mode: true,
            volume: 0.25,
            print_fps: false,
        };
        save_settings(&p, &settings).unwrap();
        let read = load_settings(&p).unwrap();
        assert!(read.fullscreen && read.touch_mode);
        assert_eq!(read.volume, 0.25);
        std::fs::write(p.join("settings.plist"), "bad").unwrap();
        assert!(load_settings(&p).is_err());
        std::fs::remove_dir_all(p).unwrap();
    }
}
