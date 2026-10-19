# Gates: desktop performance regression

Scope: restore responsive normal desktop play through make dev and make run, preserving saves and original game timing.

- [x] G1: Desktop slowdown has a measured cause and the corrected build reaches menus and gameplay at normal speed
  CHECK: python3 scripts/check_gameplay_performance.py target/qualification/performance/fixed-native --hud-template target/qualification/startup/hud-control.png --slow-control target/qualification/performance/control-native-raised/run-01
  EXPECT: GAMEPLAY_PERFORMANCE_VERIFIED
  EVIDENCE: exit=0; shell=/bin/bash; cwd=/home/aurelio/Repos/redegpc; EXPECT=matched; output-sha256=385de9511ba4d2d0320ee1020cdb68e877910327a8d5fa5a75d5a0459e13f506; output-bytes=419; log=target/qualification/performance/comparison-check.log

- [x] G2: Release binaries, formatting, focused lint, library and CLI checks pass
  CHECK: python3 scripts/verify.py
  EXPECT: REDEGPC_CHECKS_PASSED
  EVIDENCE: exit=0; shell=/bin/bash; cwd=/home/aurelio/Repos/redegpc; EXPECT=matched; output-sha256=0aedf76a7416075693296f8bf1fcd9139fe04dfea2a5acd952649ce65d8dde4c; output-bytes=7219; log=target/qualification/performance/verification-final.log

- [x] G3: Corrected desktop measurements and regression checks are independently reviewed
  EVIDENCE: Compared the control executable with the patched executable; only the explicit swap-interval call differs. Both use the Radeon GL2 renderer. Independently recounted actual EAGL FPS: control 8.06–17.98, corrected 58.60–60.22 across two runs. Reviewed world/movement and pause captures; release hash matches tested executable. Benchmark no longer forces vblank_mode=0; pointer input raises the test window. No real save directory was used.
