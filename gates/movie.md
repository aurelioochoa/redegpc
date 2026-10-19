# Gates: local intro playback

OWNS: src/frameworks/media_player/**, src/window/movie.rs, gates/movie.md

Scope: Decode local movies through FFmpeg, present video and audio in the runtime window, and deliver finish reasons only from the guest run loop.

- [x] G1: Movie decoder and lifecycle tests pass, including malformed input and cancellation
  CHECK: cargo test --locked --lib frameworks::media_player::movie_player:: -- --nocapture
  EXPECT: test result: ok
  EVIDENCE: exit=0; shell=/bin/sh; cwd=/home/aurelio/Repos/redegpc; path=92761dbdc03f/34 entries; EXPECT=matched; output-sha256=d8ef68afca1b87fa03f96533c054831a0555fec1d3569468070a0644b9a98bb7; output-bytes=1150

- [x] G2: The supplied intro decodes with nonempty video and audio through the production decoder
  CHECK: REDEGPC_TEST_MOVIE=/tmp/redegpc-media/Payload/residentevil.app/intro.mp4 cargo test --locked --lib movie_supplied_intro -- --ignored --nocapture
  EXPECT: test result: ok
  EVIDENCE: exit=0; shell=/bin/sh; cwd=/home/aurelio/Repos/redegpc; path=92761dbdc03f/34 entries; EXPECT=matched; output-sha256=f5cfff867393c2fa2700fd29da0e197960685b16f1f7d42d5d9e6d80bb880c17; output-bytes=414

- [x] G3: Modified Rust sources satisfy rustfmt
  CHECK: rustfmt --edition 2021 --check src/frameworks/media_player/movie_player.rs src/frameworks/media_player/movie_player/decoder.rs src/window/movie.rs && echo movie-format-passed
  EXPECT: movie-format-passed
  EVIDENCE: exit=0; shell=/bin/sh; cwd=/home/aurelio/Repos/redegpc; path=92761dbdc03f/34 entries; EXPECT=matched; output-sha256=e1b27c8d09d9851d44419c204f4ac21d20003259f642baadff9ea11d75ad097a; output-bytes=20

- [x] G4: Actual guest intro displays and emits audio, natural completion and skipping return guest control
  EVIDENCE: English v1.03.00 runs 3/4; actual intro frames and isolated PulseAudio capture in target/qualification/media/evidence.json; native completion Ended returned to game cutscene; Space skip produced UserExited and returned to Loading/game in /tmp/redegpc-run4.log.

Implementation/review notes: completed implement, expert review, defect hunt,
and polish passes. Decoder subprocesses use local private temporary input,
file/pipe protocol allowlist, 60-second decode cap, 64 MiB input limit and a
three-frame bounded channel. Cancellation drops the receiver and the worker
kills and waits for its child. SDL resources live in Window and are accessed
on the parent stack; notification objects are retained until guest main-run-loop
dispatch, including failure and user-exit reason metadata. Original simulated
behavior is retained outside the typed game runtime.

Supplementary isolated decoder evidence (does not substitute for crate or guest
integration gates): rustc test harness built the production decoder against the
pinned baseline uuid library. Five tests passed (positive red-video/nonzero-audio
fixture, malformed input, private temporary cleanup, cancellation with worker
completion, cancellation during preroll). The user-supplied intro decoded to 510 RGBA frames and 1,633,942
stereo samples at 48 kHz, 17.020 seconds of audio. No assertion of audible or
visible guest playback follows from this decode-only result.
