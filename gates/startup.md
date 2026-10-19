# Gates: faster loading

Scope: reduce loading waits at launch and during game transitions, preserving decoded assets, saves and gameplay timing.

- [x] G1: Release build, formatting, focused lint, library and CLI checks pass
  CHECK: python3 scripts/verify.py
  EXPECT: REDEGPC_CHECKS_PASSED
  EVIDENCE: exit=0; shell=/bin/bash; cwd=/home/aurelio/Repos/redegpc; EXPECT=matched; output-sha256=f31d2ae584de2301660b7dcafc28e30d75687f7ab80d9e65dce429f1c72367ea; output-bytes=7220; log=target/qualification/startup/final-checks.log

- [x] G2: Decoded cache preserves all original assets and rejects a changed resource
  CHECK: python3 scripts/check_asset_cache.py --data /tmp/redegpc-loading-final/data/redegpc
  EXPECT: ASSET_CACHE_VERIFIED
  EVIDENCE: exit=0; shell=/bin/bash; cwd=/home/aurelio/Repos/redegpc; EXPECT=matched; output-sha256=c7ba3c4b42d94819de93154148d06f552cbea8a3be3b9b215852f9b981b58a2f; output-bytes=277; log=target/qualification/startup/cache-check.log

- [x] G3: Repeated actual gameplay loads are faster and maintain normal presentation timing
  CHECK: python3 scripts/check_loading_benchmark.py target/qualification/startup/final-original target/qualification/startup/final-cached --hud-template target/qualification/startup/hud-control.png
  EXPECT: LOADING_COMPARISON_VERIFIED
  EVIDENCE: exit=0; shell=/bin/bash; cwd=/home/aurelio/Repos/redegpc; EXPECT=matched; output-sha256=4cfcd2ff9ea748378df6dc99628e22392d89172ebb976e0427c5ee01b0e9d5ee; output-bytes=507; log=target/qualification/startup/comparison-check.log
