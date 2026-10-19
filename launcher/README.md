# Incident dossier launcher

## Install and open the launcher

The supported build environment is Linux x86_64. Start in the repository directory. You need the Rust and native build dependencies listed in the [main README](../README.md), plus **Python 3.10+, Tk and Pillow** for this launcher, and **FFmpeg** for the game's intro video/audio.

Install your distribution's Tk/Python bindings and Pillow packages. For example, Arch uses `tk` and `python-pillow`; Debian/Ubuntu use `python3-tk` and `python3-pil`. To use the project's Pillow version range in a virtual environment after installing Tk (and your distribution's Python venv package if needed):

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r launcher/requirements.txt
```

Check dependencies in the same terminal you will launch from:

```sh
python3 -c 'import tkinter; from PIL import Image, ImageTk; print("Launcher dependencies ready")'
ffmpeg -version
```

Build and open it:

```sh
git submodule update --init --recursive
make launcher
```

`make launcher` (also `make dev`) builds the optimized game host and opens the native launcher. Compilation can take time on the first run. Once built, open it directly with `./target/release/redegpc launcher`. It needs a graphical desktop; an SSH session without a display cannot show the window. There are no web services or browser dependencies.

Run `make desktop` to add **Resident Evil Degeneration** to your desktop and applications menu with your saved icon choice (Leon by default). Both open the dossier launcher without a terminal. If your desktop asks, choose **Allow Launching** / **Trust this launcher**. The shortcuts point to this checkout; keep it in place and rerun the command after moving it. If you use a virtual environment, run `make desktop PYTHON=.venv/bin/python` to retain that interpreter for desktop launches. In **Settings & controls → Desktop icon**, choose **Leon**, **Dossier**, or **Fractured D**, then click **Apply desktop icon**. The previews are selectable with the mouse or Tab and Enter/Space. Applying updates both shortcuts and the launcher window icon immediately and remembers the choice across restarts and `make desktop`. It also creates the shortcuts if they are missing. Icon selection is separate from game settings and does not require **Save settings**.

The command also installs `~/.local/bin/redegpc`: no arguments opens the launcher, while commands such as `redegpc check` and `redegpc run` use the game host. `make uninstall-desktop` removes the shortcuts and icon while preserving the checkout, imported game and saves. For an applications-menu entry only, build first and run `python3 scripts/install_desktop.py` without `--desktop`.

## Import your game

1. Prepare your own **Resident Evil: Degeneration**, **English iPhone v1.03.00**, as a single `.ipa` file. Its bundle identifier must be `jp.co.capcom.residentevil.en`. The game is not included. Other versions, languages and encrypted App Store executables are rejected; renaming an archive does not change its version or remove DRM.
2. Open **Installation → Choose game IPA…** and select the archive. Do not unzip it first. Wait for the import to finish: the host copies the game to local storage, validates it and records file hashes. The status becomes **Ready to play** after success.
3. Return to **Overview → Play**. The first launch prepares a local cache, so allow extra time and keep the game open. Later launches reuse this cache. Once the import has completed, the source archive and external drive are no longer needed.

An existing installation is verified when the launcher opens. **Verify installation** repeats the file checks; it does not install a missing game. If import or verification fails, open **View logs** for the precise reason. Check the supported version, encryption and archive integrity, then re-import a valid copy if needed. Rejected imports preserve the previous installation and saves. If Play is disabled, wait for verification to finish and check its result in the status line or logs.

The imported files and saves live in `$XDG_DATA_HOME/redegpc` (default `~/.local/share/redegpc`); saves are under `touchHLE_sandbox`. Settings use `$XDG_CONFIG_HOME/redegpc` (default `~/.config/redegpc`), and logs use `$XDG_STATE_HOME/redegpc/logs` (default `~/.local/state/redegpc/logs`). The Installation page shows the actual data directory. Clearing the cache can be recovered on next launch; removing the data directory also removes your saves.

Direct play remains available with `make run` and `redegpc run`. For command-line import, use `make import IPA="/path/to/game.ipa"`, then `make check-install`.

## Window and navigation

See [screenshots of all four pages at normal, minimum, tall and wide sizes, plus fullscreen](../docs/launcher/README.md).

The overview follows the incident dossier concept using the separate images in `assets/`. The dossier and its live controls scale together in proportion and stay centered. Extra room in tall or wide windows reveals more desk around the composition. Header and footer span the window. Photographs fit completely, including their worn borders and rotated corners; icons and title artwork also retain their proportions. The minimum window size is 1000×620.

F11 or the expand button in the top bar toggles **launcher fullscreen**. Escape leaves fullscreen, then returns to Overview on the next press. The game display setting in **Settings & controls** applies separately to the next game launch; F11 also toggles fullscreen while the game has focus.

All buttons and labels are live. Tab / Shift-Tab moves between controls, Enter / Space activates them, and Ctrl-L opens logs. Achievements support category filters, arrow keys, Page Up / Page Down and mouse-wheel paging **over the achievement list**. Wheel input is grouped during rapid scrolling; scrolling over navigation or logs does not change the selected achievement. These are proposed goals: gameplay tracking is not implemented and the launcher does not invent unlocks.

Import opens a native IPA picker and delegates validation/copying to the Rust host. An installed game is verified asynchronously on startup. Play becomes available after successful verification; the host also verifies again before running. Import, verification and play run in children while the launcher remains responsive. Overlapping operations are disabled. Closing during import waits for completion; closing during play asks before ending the game. Failed operations show their error and retain output in the log viewer.

Settings use the host's existing `settings.plist` in the same XDG config directory. Save applies display, input and volume preferences on the next launch. Unsaved edits are kept while navigating but do not affect Play. Invalid preferences are reported in logs; Reset defaults repairs them when selected. Runtime logs are read from the same XDG state directory as the CLI. The log viewer updates while open and supports selection/copying and Ctrl-R refresh.

To run directly from another working directory:

```sh
python3 /path/to/redegpc/launcher/main.py --binary /path/to/redegpc/target/release/redegpc
```

For a relocated installation, place this directory (including assets and `achievements.json`) beside the host executable as `launcher/`, or under `share/redegpc/launcher/`. Include `touchHLE_dylibs`, `touchHLE_fonts` and `touchHLE_default_options.txt` in the host's `resources/` directory or `../share/redegpc/`, keeping their notices. Moving only the executable is insufficient. See [resource resolution](../README.md).

Verify with `make test-launcher`. For a headless Linux machine, use an Xvfb display. The interaction check uses isolated XDG directories, a synthetic process fixture and the real host's import/check commands; it does not modify an existing game installation or saves.

For focused desktop-icon checks, run `python3 scripts/verify_launcher.py --icons-only`. This exercises all three choices, desktop and applications-menu files, persistence after restart and reinstall, write failures, and six settings-page sizes using an isolated home directory. When installed, `desktop-file-validate` also checks the generated shortcuts.
