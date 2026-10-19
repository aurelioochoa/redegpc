# Resident Evil Degeneration PC Port

**English** · [Español](README.es.md)

![Resident Evil Degeneration — Leon and Claire at the airport](docs/media/banner.png)

Play the English iPhone release of **Resident Evil Degeneration** on Linux with keyboard and mouse controls, a native desktop launcher, and local saves. `redegpc` is a Rust compatibility host based on touchHLE revision `ca1de89c578e79746f33c1332e28efd106c334ba`.

**Bring your own game:** the supported release is the unencrypted **English iPhone v1.03.00 IPA**. The project does not include game files. This is an experimental preservation project; full playable compatibility has not been established.

[Gameplay](#gameplay) · [Quick start](#quick-start) · [Game files](#game-files) · [Controls](#controls) · [Development](#development)

## Gameplay

Actual Linux gameplay captured at the original **480×320** resolution.

| Airport exploration | Aiming and firing |
| --- | --- |
| ![Leon exploring the airport](docs/media/gameplay-exploration.gif) | ![Leon aiming and firing](docs/media/gameplay-aiming.gif) |
| ![Airport scene](docs/media/screenshot-airport.png) | ![Over-the-shoulder aiming](docs/media/screenshot-aiming.png) |

The banner is illustrated fan artwork; screenshots and GIFs show the running project. See [media provenance](docs/media/README.md).

## Requirements

- **Linux x86_64** with a graphical desktop.
- Rust, C/C++ compilers, CMake, Boost headers, `pkg-config`, liblzma development headers (XZ), and native SDL/OpenAL development dependencies.
- **Python 3.10+, Tk and Pillow** for the launcher.
- **FFmpeg** on `PATH` for the original intro's video and audio.

Keep `Cargo.lock` and the pinned submodules. See the [build documentation](dev-docs/building.md) and [launcher dependency guide](launcher/README.md#install-and-open-the-launcher) for platform packages and Python setup.

## Quick start

Install the system prerequisites above, then:

```sh
git clone https://github.com/aurelioochoa/redegpc.git
cd redegpc
git submodule update --init --recursive
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r launcher/requirements.txt
make launcher
```

`make launcher` builds the optimized host and opens the incident dossier launcher. In **Installation**, choose your supported IPA and wait for **Ready to play**, then use **Overview → Play**. The first launch prepares a local asset cache and takes longer.

For direct command-line play:

```sh
CARGO_BUILD_JOBS=4 cargo build --locked --release --bin redegpc
./target/release/redegpc import "/path/to/Resident Evil Degeneration - v1.03.00.ipa"
./target/release/redegpc check
./target/release/redegpc run
```

## Game files

Only bundle **`jp.co.capcom.residentevil.en`**, version **`1.03.00`**, with an **unencrypted ARM Mach-O** is supported. Select the intact `.ipa`; do not extract it first. Other versions, languages and encrypted executables are rejected.

Import validates the app, copies it to local storage, records SHA-256 hashes and switches installations only after success. Rejected imports preserve existing installations and saves. After import, the source IPA and external drive are no longer needed. `check` verifies the installed originals; the decoded cache is separate and can be regenerated.

See [import and recovery details](launcher/README.md#import-your-game) and the [detailed usage guide](docs/advanced-usage.md#build-and-play).

## Launcher

![Native incident dossier launcher](docs/launcher/overview-1000x620.png)

- **Installation:** import and verify the game.
- **Overview:** play after verification succeeds.
- **Settings & controls:** save display, input and volume preferences for the next launch; choose a desktop icon.
- **Achievements:** browse 23 proposed goals and category filters. Gameplay achievement tracking is not implemented.
- **View logs:** inspect import, verification and runtime output.

F11 toggles launcher fullscreen independently of the game's display preference. Tab and Shift-Tab move between controls; Enter or Space activates them.

Run `make desktop` to install the applications-menu entry, desktop shortcut and `~/.local/bin/redegpc`. With an active virtual environment, use `make desktop PYTHON=.venv/bin/python`. The installed command opens the launcher without arguments; `redegpc run` starts the game directly. Keep this checkout in place. `make uninstall-desktop` removes the integration while preserving game files and saves. See the [full launcher guide](launcher/README.md).

## Controls

| Input | Action |
| --- | --- |
| W / A / S / D or arrows | Move |
| Hold right mouse and move mouse | Aim |
| Left mouse while aiming | Fire |
| R | Reload |
| Hold Space | Shake off a grab |
| E | Contextual action |
| Tab | Open inventory |
| Escape | Pause / back |
| F11 | Toggle game fullscreen |

Menus retain normal pointer navigation. Desktop mode hides the original movement, aim/fire, knife and walk graphics while keeping contextual actions, health, ammo and the phone shortcut visible. E follows the current contextual icon; without a nearby interaction it can enter the game's native aim mode. Losing focus releases held inputs.

Use `./target/release/redegpc run --touch` for original touch controls. Other options include `--fullscreen`, `--windowed`, `--volume=0..100` and `--fps`; display, input and volume settings persist. Escape, Enter, Space or a click skips the movie. See [detailed runtime behavior](docs/advanced-usage.md#build-and-play).

## Saves and settings

| Content | Default location |
| --- | --- |
| Imported installations, manifest and cache | `~/.local/share/redegpc` |
| Saves | `~/.local/share/redegpc/touchHLE_sandbox` |
| Settings and upstream options | `~/.config/redegpc` |
| Runtime log | `~/.local/state/redegpc/logs/redegpc.log` |

`XDG_DATA_HOME`, `XDG_CONFIG_HOME` and `XDG_STATE_HOME` override the corresponding base directories. Clearing the asset cache is recoverable; deleting the data directory also deletes saves. Previous installations are retained, and an OS lease prevents overlapping runtimes from using the same saves.

## Status and limitations

The project is under local qualification. A successful build or a gameplay capture does not establish full campaign compatibility. Read the [observed results and remaining defects](docs/qualification.md) and [acceptance gates](GATES.md) before assessing support.

The runtime preserves the game's original resolution and timing. Cached asset decoding improves later loads while keeping imported originals intact. The launcher can browse proposed achievements but does not award them. Current platform support targets Linux x86_64.

## Development

| Command | Purpose |
| --- | --- |
| `make help` | Show available targets |
| `make setup` | Initialize submodules, fetch locked dependencies and check launcher prerequisites |
| `make build` | Build the release host |
| `make dev` / `make launcher` | Build and open the native launcher |
| `make run ARGS="--windowed --fps"` | Run with extra options |
| `make check-game` | Verify imported game files (`check-install` is an alias) |
| `make check` | Check Rust without linking |
| `make verify` | Build and run formatting, focused Clippy, library and synthetic CLI checks |
| `make test-launcher` | Run isolated launcher checks on a graphical display |
| `make clean` / `make distclean` | Remove Python caches / also clean Cargo artifacts |

Builds default to four Cargo jobs; override with `CARGO_BUILD_JOBS=8 make build`. Cleaning preserves game files and saves. The inherited runtime remains available with `cargo run --locked --release --bin touchHLE -- ...`.

See [detailed usage, architecture and qualification tools](docs/advanced-usage.md), [loading measurements](docs/qualification.md#loading-optimization-2026-10-16), and the [upstream README](README.touchHLE.md).

Contributions use this repository's GitHub issues and pull requests. Read the bilingual [contribution guide](CONTRIBUTING.md#english) and [piracy policy](CODE_OF_CONDUCT.md#english).

## License and credits

Based on **touchHLE**, retaining its history and notices. New host and compatibility code follows **MPL-2.0** source notices; the documented combined binary is **GPL-3.0-or-later**. Individual components retain their licenses. See [LICENSE](LICENSE), [upstream terms](README.touchHLE.md) and [redegpc notices](NOTICE.redegpc.md).

Resident Evil Degeneration and its game assets belong to their respective owners. The game is not distributed here; runtime resources and dependencies retain their required notices.
