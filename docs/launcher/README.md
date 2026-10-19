# Native launcher captures

These are captures of the implemented Tk launcher using the supplied individual artwork, live text and native controls. They were taken on an X11 virtual display after the Rust host verified a private copy of the real imported game. The original installation and saves were preserved.

The dossier keeps one proportional scale and stays centered as the window changes shape. Extra width or height exposes more desk; photographs retain their complete borders and rotated corners. Header and footer continue to span the window.

| Page | 1440 × 810 | Minimum 1000 × 620 |
| --- | --- | --- |
| Overview | [Open](overview-1440x810.png) | [Open](overview-1000x620.png) |
| Achievements | [Open](achievements-1440x810.png) | [Open](achievements-1000x620.png) |
| Settings & controls | [Open](settings-1440x810.png) | [Open](settings-1000x620.png) |
| Installation | [Open](installation-1440x810.png) | [Open](installation-1000x620.png) |

Resize review also includes a tall **1000×900** window and a wide **1920×810** window:

| Page | Tall | Wide |
| --- | --- | --- |
| Overview | [Open](overview-1000x900.png) | [Open](overview-1920x810.png) |
| Achievements | [Open](achievements-1000x900.png) | [Open](achievements-1920x810.png) |
| Settings & controls | [Open](settings-1000x900.png) | [Open](settings-1920x810.png) |
| Installation | [Open](installation-1000x900.png) | [Open](installation-1920x810.png) |

[Fullscreen installation](installation-fullscreen.png) shows the launcher occupying the display. F11 and the top-bar expand control toggle launcher fullscreen; Escape restores the previous window size. The game's fullscreen preference is independent.

The achievements page browses the complete goal catalog and explicitly reports that gameplay tracking is not available. Displayed installation readiness comes from a successful host check.

Reproduce on a graphical X11 display with `python3 scripts/capture_launcher.py`. Add `--play` to activate Play, skip the intro, compare the real title menu with a reviewed local capture, close the game normally, and verify the launcher returns to Ready. `--template` selects the reviewed title-menu capture. Runtime evidence remains local under `target/qualification/launcher/`.

Automated interaction coverage is in `scripts/verify_launcher.py`; it includes real import and file corruption checks, settings persistence and recovery, log updates, category filtering and all achievement goals, keyboard activation, six window sizes, fullscreen/restore, bounded process output, shutdown and the public Rust launcher command from an unrelated working directory. Wheel checks send queued Linux button events and Windows-style deltas over live rows, including zero/fractional deltas, long bursts, both list boundaries, filters and navigation while a render is pending. Use `--require-fullscreen` with a fullscreen-capable window manager to require actual display-sized geometry rather than checking toggle state alone.
