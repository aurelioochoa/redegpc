# Gates: launcher polish

OWNS: launcher/**, scripts/verify_launcher.py, scripts/capture_launcher.py, docs/launcher/**, README.md, gates/launcher-polish/**

Scope: remove resize letterboxing, provide launcher fullscreen, stabilize achievement wheel input, review asset presentation and explain installation.

- [x] P1: Resize and fullscreen cover the actual viewport and preserve usable controls; wheel bursts remain stable across filters and boundaries; existing launcher interactions pass
  CHECK: DISPLAY=:96 python3 scripts/verify_launcher.py --require-fullscreen
  EXPECT: LAUNCHER_CHECKS_PASSED
  CWD: ../..
  EVIDENCE: exit=0; shell=/bin/sh; cwd=/home/aurelio/Repos/redegpc; path=08544ba07d97/32 entries; EXPECT=matched; output-sha256=b8bdfff3b5a17e2b9f3d0800d21b99df15dd779c38d2f13a21e5fa20db3800ef; output-bytes=121

- [x] P2: All production artwork and achievement image references validate
  CHECK: python3 launcher/artwork/verify_assets.py
  EXPECT: LAUNCHER_ARTWORK_VERIFIED
  CWD: ../..
  EVIDENCE: exit=0; shell=/bin/sh; cwd=/home/aurelio/Repos/redegpc; path=08544ba07d97/32 entries; EXPECT=matched; output-sha256=e9346d29c6b1763c4dda149aaabe7f61e72f3405ad3161e84cc2481608890669; output-bytes=82

- [x] P3: All pages visually reviewed at standard, tall and wide sizes, including achievement selection and installation guidance
  EVIDENCE: Reviewed docs/launcher captures at 1440x810, 1000x620, 1000x900 and 1920x810 plus actual 2560x1440 fullscreen; independently verified all 17 image dimensions. No letterbox bands; controls align with expanded paper surfaces, airport photos crop proportionally, portraits preserve both faces, title/stamps/achievement art remain proportional. Reviewed launcher/artwork/after.jpg and selected goal details from wheel/filter tests. DISPLAY=:96 python3 scripts/capture_launcher.py --play passed using private installation/saves; target/qualification/launcher/result.json records real menu similarity=1.0 and clean game close with current binary SHA-256.

- [x] P4: Installation instructions explain dependencies, supported IPA, import, first launch, troubleshooting and storage consistently with the host
  EVIDENCE: Reviewed launcher/README.md and README.md against src/redegpc/mod.rs, import.rs, asset_cache.rs and launcher/backend.py. UI gives three ordered steps with exact language/version, intact unencrypted IPA, successful import status, Play, local storage, cache preparation and logs. Documentation covers Tk/Pillow setup, source-drive independence, storage, resources and independent launcher/game fullscreen.
