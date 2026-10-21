# Launcher artwork audit and regeneration

Visual targets: `docs/launcher-concepts/03-incident-dossier.png` and `04-achievements.png`.

The original folder contained full-screen concepts mixed with production cutouts, experiment crops and raw generations. Several assets were extracted from a flattened mockup instead of being independent objects:

| Group | Observed problem | Regeneration contract |
| --- | --- | --- |
| Menu icons | Included adjacent icons, paper, dividers and cropped UI | Three standalone transparent medal, gear and briefcase icons |
| Airport photograph | Included blueprint and overlapping character photo | One complete level photograph with its own worn border |
| Character photographs | Included neighboring photographs and desk fragments | Independent Leon, Claire and paired portraits, colorized at the user's request |
| Achievements | Mixed dimensions, palette and framing; stray fragments on the boarding pass | Twelve standalone, centered inventory objects; first four follow the steel appearance of reference 04 |
| Raw images | Some checkerboards were actual RGB pixels | Remove obsolete raw files; retain new full-resolution RGBA artwork in `sources/` |
| Paper | `paper.png` and `case-paper.png` were identical; embedded confidential stamp and coffee ring differed from references | Clean reusable paper material, identical aliases retained for compatibility |
| Title and Play | Title had fragile extracted edges; button was a crop | Independent transparent title and textless red material; controls and labels remain for application rendering |
| Composition layers | Missing independent desk, blueprint, folder, detail sheet, airport stamp, clip and logs icon | Generate each layer separately |

## Scope

Forty-one unique generated assets. Existing production filenames and pixel dimensions are preserved at export. `case-paper.png` aliases `paper.png`.

The user's follow-up adds seven weapon trophies (Handgun, Punisher, Shotgun, Riot Gun, TMP, Rifle and Magnum), three difficulty medals (Easy, Normal and Professional), and a platinum emblem. The resulting 23-entry `launcher/achievements.json` catalog specifies platinum as requiring all 22 other achievements. Weapon goals reward full upgrades; these and the story goals are launcher achievement design, not original official achievements or implemented tracking.

Weapon names, upgrade attributes and difficulty labels were checked against the original iPhone [walkthrough](https://gamefaqs.gamespot.com/iphone/960237-resident-evil-degeneration/faqs/57543) and [author's difficulty notes](http://sephirosuy.blogspot.com/2009/08/re-degeneration-game-basic.html) using agent-reach's Exa search route.

At the user's request, obsolete `overview.png`, `achievements.png`, `achievement-atlas.png`, `test_*.png` and `raw_*.png` are removed from `launcher/assets`. The two authoritative concept images remain in `docs/launcher-concepts`. Original checksums and dimensions are recorded in `baseline.json`; the pre-replacement backup was moved outside the project to `/tmp/redegpc-launcher-assets-before-20261017/`.

## Generation and export

Built-in image generation, one call per individual asset, with the two concept images supplied as visual references. Full-resolution outputs are saved in `sources/` and must be retained. No CLI/API fallback is used.

`export_assets.py` only resizes and pads/crops generated artwork using ImageMagick; it does not draw, extract backgrounds, or synthesize artwork. Transparent output alpha is retained. The manifest records source and final checksums, dimensions, alpha statistics and aliases. `after.jpg` shows the final individual exports against contrasting backgrounds for visual review.

This task produces artwork. It does not implement the native launcher or establish runtime visual parity with the full-screen concepts.

## Final validation

The export and verification commands both exited successfully. The active folder contains 42 PNGs: 41 independently generated assets and the identical paper compatibility alias. All 23 achievement catalog entries resolve to their artwork; platinum references exactly the other 22 achievements. Negative controls rejected a stale output digest and an incomplete platinum dependency set. Portrait color checks pass, original production dimensions remain unchanged, and the complete final contact sheet was visually reviewed against light and dark backgrounds. Six acceptance gates met; zero unmet or abandoned.
