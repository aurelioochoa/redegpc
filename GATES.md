# Gates: redegpc playable core

Scope: implement and qualify the supplied English v1.03.00 game on the pinned Rust touchHLE runtime.

- [x] G1: Locked release binaries build and project formatting, focused lint and relevant tests pass
  CHECK: python scripts/verify.py
  EXPECT: REDEGPC_CHECKS_PASSED
  EVIDENCE: exit=0; shell=/bin/sh; cwd=/home/aurelio/Repos/redegpc; path=92761dbdc03f/34 entries; EXPECT=matched; output-sha256=b5c87706f3140981a06c9238a47414204707f5d2a1b62b60c619c88149e7811e; output-bytes=6350

- [x] G2: Import preserves resources and rejects corrupt, unsafe, encrypted and unsupported fixtures without changing installation or saves
  CHECK: cargo test --locked --lib redegpc::
  EXPECT: test result: ok
  EVIDENCE: exit=0; shell=/bin/sh; cwd=/home/aurelio/Repos/redegpc; path=92761dbdc03f/34 entries; EXPECT=matched; output-sha256=a1558057c3a21b3a2db820450a836aa60b17b41209db26ad74275dc5f297d7a1; output-bytes=777

- [x] G3: Imported exact IPA checks and launches independently of cwd and source path
  EVIDENCE: target/qualification/source-drive-hidden.json independently observes the runtime cwd under /tmp and an empty tmpfs over T-REX; host IPA exists as a positive control while child cannot stat it. Cold-run screenshots show imported English v1.03.00 reaching menu with this namespace.

- [x] G4: Twenty consecutive cold launches reach the menu
  CHECK: python scripts/check_qualification.py target/qualification/cold-20-shake-final
  EXPECT: COLD_LAUNCH_ARTIFACTS_VERIFIED
  EVIDENCE: exit=0; shell=/bin/sh; cwd=/home/aurelio/Repos/redegpc; path=92761dbdc03f/34 entries; EXPECT=matched; output-sha256=0ba532a07299baee84b4a3bfd591a6a209498520e0edb00c86026b0989ea26af; output-bytes=160

- [x] G5: Intro video and audio, completion and skip, all keyboard/mouse actions and focus recovery work in supplied game
  EVIDENCE: Final build 5162e4c9 natural intro/video/audio/Ended plus source-hidden touch launch in target/qualification/final-media; earlier UserExited skip in media. Final mouse hits, reload, E loot/ladder/window/door, inventory, focus recovery in controls/final. Independent active soak recount passes; chapter progression remains G6.

- [ ] G6: Thirty minutes gameplay, first chapter and next transition, save/exit/restart/reload preserve progress
  EVIDENCE: pending

- [x] G7: Pinned upstream history, dependency revisions and all source/resource/binary notices preserved
  EVIDENCE: git ancestry check and diff of Cargo.lock/LICENSE/.gitmodules/vendor/resource trees exited 0; README.touchHLE.md byte-equals pinned README; runtime dependency/resource notices and dev-scripts/gpl-3.0.txt retained; --copyright verified by CLI check.

- [ ] G8: Frame pacing, load times, screenshots and remaining defects recorded from local execution
  EVIDENCE: pending
