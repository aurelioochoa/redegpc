# Gates: incident dossier launcher

Scope: implement the supplied dossier overview and achievements designs as a native launcher using the existing artwork, and connect installation, settings, launch and logs behavior. Achievement goals are browsable; runtime tracking is outside this launcher task.

- [x] L1: Native overview and achievement browser use the supplied individual assets and visually follow both references
  EVIDENCE: Reviewed docs/launcher/overview-1440x810.png and achievements-1440x810.png against both supplied concepts; live paper controls, separate artwork, airport photographs and selected goal details; minimum-size captures also reviewed.

- [x] L2: Launcher navigation, input, installation errors, settings persistence and process lifecycle pass automated interaction checks
  CHECK: DISPLAY=:96 python3 scripts/verify_launcher.py
  EXPECT: LAUNCHER_CHECKS_PASSED
  EVIDENCE: /bin/bash; cwd=/home/aurelio/Repos/redegpc; exit=0; match=LAUNCHER_CHECKS_PASSED; output sha256=b8bdfff3b5a17e2b9f3d0800d21b99df15dd779c38d2f13a21e5fa20db3800ef, 121 bytes; /tmp/redegpc-launcher-ui-checks.log

- [x] L3: Release build, formatting, focused lint and existing CLI and library regressions pass
  CHECK: python3 scripts/verify.py
  EXPECT: REDEGPC_CHECKS_PASSED
  EVIDENCE: /bin/bash; cwd=/home/aurelio/Repos/redegpc; exit=0; match=REDEGPC_CHECKS_PASSED; output sha256=17a63b8cec327b149fc43a3072c564a0776428d8b4e3d224f03df4fae8db8675, 7405 bytes; /tmp/redegpc-launcher-rust-checks.log

- [x] L4: The real imported game launches through the launcher and screenshots document overview, achievements, settings and installation at normal and minimum size
  EVIDENCE: DISPLAY=:96 python3 scripts/capture_launcher.py --play; exit=0; LAUNCHER_CAPTURE_PASSED; target/qualification/launcher/result.json verifies real menu similarity=1.0 and clean game close using a private copy of saves; all eight captures in docs/launcher/; current binary SHA-256 matches recorded launch.
