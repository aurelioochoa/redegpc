# Gates: Degeneration controls

OWNS: src/redegpc_controls.rs, src/window.rs, src/options.rs, gates/controls.md

Scope: opt-in desktop action layer with deterministic multi-key touches, clickable menus, movie input isolation and focus recovery.

- [x] G1: movement aliases, opposing keys, repeated events, shared actions and focus clearing produce balanced touch events
  CHECK: rustc --edition=2021 --test src/redegpc_controls.rs -o /tmp/redegpc-controls-tests && /tmp/redegpc-controls-tests
  EXPECT: test result: ok.
  EVIDENCE: exit=0; shell=/bin/sh; cwd=/home/aurelio/Repos/redegpc; path=92761dbdc03f/34 entries; EXPECT=matched; output-sha256=fe7c3cd328241e25512a5def1a0ed5b9dd6b188eebb1e49552b3e46d5834321a; output-bytes=487

- [x] G2: changed Rust files conform to project formatting
  CHECK: rustfmt --edition 2021 --check src/redegpc_controls.rs src/window.rs src/options.rs
  EXPECT: /^$/
  EVIDENCE: exit=0; shell=/bin/sh; cwd=/home/aurelio/Repos/redegpc; path=92761dbdc03f/34 entries; EXPECT=matched; output-sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855; output-bytes=0

- [x] G3: game input maps movement, relative mouse aim/fire, reload, Space shake-off, interaction, inventory and pause to their observed in-game actions; focus recovery clears held touches
  EVIDENCE: actual English v1.03.00 runs 3/4/standalone; target/qualification/controls contains inventory, aim/fire/release, reload 13-to-15, E ladder interaction, focus-before/after recovery, fullscreen 1600x900 pillarboxed to 1350x900 and restored 480x320 captures. SDL input traces in /tmp/redegpc-play.log; timed action tests cover aliases/opposites/repeats/menu cancellation.

Final control follow-up: 11 focused state tests pass; actual relative mouse
steering hits moving enemies, E picks up/accepts $100 loot, R reloads while
aiming, and focus recovery releases captured mouse motion on binary 5162e4c9.
Space released a supplied-game grab in the shake candidate; its waveform and
coordinate transform are unchanged in the final build. Artifacts are under
target/qualification/controls/final and /tmp/redegpc-private/grab-*-space.png.
