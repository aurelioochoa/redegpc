# Incident dossier launcher assets

`desktop-icons/` contains the three transparent desktop icon concepts: `leon-portrait.png`, `quarantine-dossier.png`, and `fractured-d.png`. These are runtime copies of the original concepts in [docs/desktop-icons](../../docs/desktop-icons/), where the image generation prompts are retained. Settings displays all three and installs the selected PNG without altering its artwork.

Standalone regenerated artwork based on the [overview concept](../../docs/launcher-concepts/03-incident-dossier.png) and [achievements concept](../../docs/launcher-concepts/04-achievements.png).

| Role | Files | Rendering notes |
| --- | --- | --- |
| Backdrop | `desk-background.png`, `airport-blueprint.png` | Dark desk fills the window; transparent blueprint overlays it |
| Dossier | `dossier-folder.png`, `detail-paper.png` | Transparent outer margins; blank centers accept live text and controls |
| Paper material | `paper.png`, `case-paper.png` | Identical opaque material aliases; no baked labels or stamps |
| Title | `title-logo.png` | Transparent navy title, includes PC PORT subtitle |
| Primary control | `play-plate.png` | Opaque red texture; application draws Play text and triangle |
| Evidence photos | `photo-airport.png`, `photo-leon.png`, `photo-claire.png`, `photo-protagonists.png` | Color airport, Leon, Claire and paired photographs with ivory borders; rotate during layout |
| Overlays | `quarantine-stamp.png`, `airport-stamp.png`, `paperclip.png` | Transparent ink/metal; position independently |
| Navigation | `icon-achievements.png`, `icon-settings.png`, `icon-import.png`, `icon-logs.png` | Transparent objects; labels remain live text |
| Achievements | `achievement-first-contact.png`, `achievement-clear-terminal.png`, `achievement-fully-equipped.png`, `achievement-survivor.png`, `achievement-hero.png`, `achievement-mercenary.png`, `achievement-upgrades.png`, `achievement-escape.png`, `achievement-cargo.png`, `achievement-gvirus.png`, `achievement-shutter.png`, `achievement-vip.png` | Twelve separate objects with genuine transparency; locked state and progress belong to the application |
| Weapon achievements | `achievement-handgun.png`, `achievement-punisher.png`, `achievement-shotgun.png`, `achievement-riot-gun.png`, `achievement-tmp.png`, `achievement-rifle.png`, `achievement-magnum.png` | Seven distinct firearm illustrations; proposed goals reward fully upgrading each weapon |
| Difficulty achievements | `achievement-difficulty-easy.png`, `achievement-difficulty-normal.png`, `achievement-difficulty-professional.png` | Bronze, silver and gold campaign medals with one, two and three stars |
| Platinum | `achievement-platinum.png` | Platinum shield and laurel emblem; requires all 22 other achievements |

Existing production filenames and dimensions are preserved. Use the `achievement-*.png` exports in the launcher; full-resolution generated originals are stored separately in `../artwork/sources/`.

The launcher renders the desk across the actual viewport and centers the dossier composition above it. Artwork and live controls share one uniform scale, so tall and wide windows add desk space instead of distorting the paper columns. Title, stamps, icons and achievement illustrations fit their layout bounds without changing proportions. All photographs fit completely, including their ivory borders and rotated corners. Header and footer span the window, including fullscreen; text and controls remain live widgets.

Obsolete `overview.png`, `achievements.png`, `achievement-atlas.png`, `test_*.png` and `raw_*.png` have been removed. The two concept references remain in `docs/launcher-concepts/`.

The [audit](../artwork/AUDIT.md), full-resolution `../artwork/sources/`, [original metadata](../artwork/baseline.json), and [manifest](../artwork/manifest.json) document regeneration using the built-in image generation tool. The original backup is outside the project at `/tmp/redegpc-launcher-assets-before-20261017/`.

The [achievement catalog](../achievements.json) links all 23 achievement images to titles and proposed goals, with an explicit complete dependency set for platinum. This is artwork and design data; runtime tracking is not implemented by these files.

Export and verify with Python 3, Pillow and ImageMagick installed:

```sh
python3 launcher/artwork/export_assets.py
python3 launcher/artwork/verify_assets.py
```

The [before preview](../artwork/before.jpg) and [after preview](../artwork/after.jpg) are contact sheets for reviewing individual artwork. These files do not implement or test the launcher interface.
