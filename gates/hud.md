# Gates: desktop contextual HUD

OWNS: src/redegpc/hud.rs, src/redegpc/mod.rs, src/frameworks/opengles/gles_guest.rs, src/frameworks/opengles/eagl.rs, src/window.rs, src/redegpc_controls.rs, README.md, gates/hud.md

Scope: remove desktop mouse access to hidden touch controls while retaining a visible, clickable phone, contextual keyboard actions, menus and original touch-mode input.

- [x] G1: Render and mouse filtering preserve the phone, contextual sprites and menus; project build, formatting, lint and library checks pass
  CHECK: python scripts/verify.py
  EXPECT: REDEGPC_CHECKS_PASSED
  EVIDENCE: exit=0; shell=/bin/sh; cwd=/home/aurelio/Repos/redegpc; path=08544ba07d97/32 entries; EXPECT=matched; output-sha256=1553400823ea0a21fe747bd434c972f7aaaa03e4e9ae7e7b7224d2ad0b7738d4; output-bytes=7582

- [x] G2: Actual desktop clicks cannot activate hidden controls or disrupt keyboard movement/aim; the phone is visible and clickable, menus work, E activates a contextual prompt, and touch mode retains controls
  EVIDENCE: target/qualification/hud/input-evidence.json records the final binary and capture hashes plus successful texture, frame-classifier and 13 control regression checks. Reviewed desktop-input-final/before-hidden-clicks.png and after-hidden-clicks.png: W movement survives clicks at the former pad, aim, knife and walk targets without changing modes. phone-map.png, phone-items.png and phone-closed.png show restored phone click navigation; mapped-aim.png, mapped-fire.png and mapped-aim-released.png verify mapped aim/fire/release after closing the phone (15 to 14 rounds). context-prompt.png, context-climbing.png and context-complete.png verify E ladder interaction. touch-input-final/native-touch-aim.png and native-touch-movement.png verify original graphics and native mouse input in touch mode. Runtime logs confirm gameplay/menu pointer routing transitions; both runtime sessions exited 0. Original installation check verifies all 18 files; gameplay used disposable saves.
