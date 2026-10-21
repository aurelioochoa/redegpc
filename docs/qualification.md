# Local qualification

Target: Linux x86_64, English jp.co.capcom.residentevil.en v1.03.00.
Base: ca1de89c578e79746f33c1332e28efd106c334ba. This is an evidence log;
unchecked acceptance gates remain required work.

## Baseline and defects

An unmodified, dynamically linked release baseline built from a separate git
worktree (`cargo build --locked --release --no-default-features --bin touchHLE`).
Its first launch stalled on a black 480×320 screen with no presented frame-rate
output. Native gdb launched as the parent (attach was unavailable) showed the
host repeatedly sleeping about 16 ms. Guest register/stack dumps showed main
inside UIApplicationMain and loader waiting on a Mach semaphore after queuing
a main-thread selector which calls MainView setNeedsDisplay. Inspection found
that Core Animation's fullscreen EAGL fast path returns before display_layers.
A pristine control run with the existing --force-composition option restored
both compositor and EAGL rendering, around 55–60 FPS after loading. The typed
Degeneration profile therefore enables that existing option; scheduling is
unchanged. Raw investigation traces are in /tmp/redegpc-baseline-*-trace.log
and /tmp/redegpc-baseline-composed.log on this machine.

A baseline restart exposed a second defect: stat(savedata1.i3d) tries to open a
host path that no longer exists after rotating the savedata files. Sequential typed-runtime runs have not reproduced it. A per-data-directory OS
lease now prevents overlapping runtime snapshots/save rotations, and a second
instance rejection was observed locally. No generic filesystem or scheduling
change was made. Full progress save/reload qualification is still required.

## Media evidence

ffprobe reports intro.mp4: MPEG-4 video, 480×270, mono AAC 44,100 Hz, duration
17.000 seconds. The production FFmpeg decoder yields 510 aspect-preserving
RGBA frames at 30 FPS and 1,633,942 stereo samples at 48 kHz (17.020 seconds).
Positive generated media verifies nonzero audio and red video pixels. Corrupt
input, cancellation during preroll and frame streaming, and private input-file
cleanup are tested. Actual guest playback is also captured in target/qualification/media: a
natural-playback frame, before/after skip frames, and evidence.json. The isolated
PulseAudio capture has 575,406 nonzero samples out of 576,000 in the six-second
middle segment (peak 7,575). Natural completion logs Ended and returns to the
game cutscene; Space skip logs UserExited and returns to game loading. No
unrelated system audio was captured: only a dedicated null sink was recorded.

## Build and importer evidence

Cargo.lock and vendor gitlinks are unchanged. The default bundled release now
builds with CMake 4.4.1/GCC 16 after configuring C17, disabling the pinned SDL's
obsolete direct PipeWire API, and supplying OpenAL's missing cstdint include.
No vendor source is patched. Existing library tests and importer fixtures passed.
Final locked release, all library tests, formatting, focused Clippy and CLI
checks pass through GATES:G1. The importer/lease subset passes GATES:G2.

The supplied IPA includes Apple's CodeResources -> _CodeSignature/CodeResources
signature alias. Import materializes that exact constrained alias as an ordinary
file, records its original target, and rejects other symlinks. Main game resource
and config bytes are unchanged. A manifest-name collision found during review
is rejected, and staged/destination content is verified before pointer commit.
A final rehash of the original open file rejects source mutation during import.

## Required live acceptance

| Outcome | Current evidence |
|---|---|
| Twenty consecutive cold launches to menu | Passed on final build 5162e4c9: 20/20; 42.978–43.256s, median 43.0075s; all exit 0; target/qualification/cold-20-shake-final |
| Visible intro + audio, natural completion and skip | Passed; target/qualification/media/evidence.json |
| Movement/combat/interact/inventory/pause/focus recovery | Passed: keyboard movement, relative mouse aim, hits on moving enemies, firing, reload, E ladder/drop/window/door/pickup, inventory, pause/back and final-build focus recovery; Space shake-off also observed |
| Thirty minutes and chapter one + transition | Pending |
| Save/exit/restart/reload | Pending; baseline save rotation defect |
| Source-drive-independent run from another cwd | Passed; target/qualification/source-drive-hidden.json plus live menu captures |
| Frame pacing and loading times | Actual presentation CSV available; preliminary 83.18s sample after 35s: median 16.668ms, p95 16.888ms, p99 21.291ms. Extended gameplay measurement pending |
| Screenshots | Live movie/menu/control captures under target/qualification and /tmp/redegpc-*.png |

No chapter, restart-reliability or playable-core certification is claimed by
this document until corresponding evidence is recorded.

## Controls verified in the supplied build

Movement requires a center touch followed by a drag. The inherited named
controller coordinates alone did not establish keyboard movement. Tab opens
phone Map then changes to Items; Escape closes the phone menu. Live captures
confirm both. The five phone pages (Map, Items, Log, Key Items, Options) were
inspected locally.

The middle right button enters aim in move mode and becomes Fire in aim mode;
the upper right button exits aim. Holding the middle button as a naive RMB
mapping could fire. Timed entry/exit taps avoid that. Live checks showed RMB
entry retaining 15 bullets, LMB reducing ammunition, and RMB release restoring
move mode. R reloaded from 13 to 15 bullets. Capstone inspection of the game's
accelerometer callback showed Airplay rotates UIKit axes again; the reload
pulse accounts for that landscape transform. Original config remains intact.

## Test environment and artifact interpretation

Offscreen X11 qualification uses Mesa vblank_mode=0 to avoid background-window
throttling; game clocks and the inherited frame limiter remain unchanged.
Cold launch runs use Bubblewrap to hide only T-REX in each child's private
mount namespace. The host mount stays available. The independent /proc check
verified an empty child drive and an inaccessible source IPA while its host
path remained a known positive control.

The chapter route was planned using the authored
[sephirosuy walkthrough](https://sephirosuy.blogspot.com/2009/08/re-degeneration-walkthrough.html).
That guide is only a route reference; it is not local execution evidence.

## Mouse steering follow-up

User testing found that the mouse buttons worked but pointer motion did not steer
the aim. The desktop handler previously ignored motion unless dragging a native
pointer touch. Relative motion is now captured while RMB is held and spent as
bounded control-pad travel, including vertical aim. Release, navigation and focus
loss free the cursor and clear pending motion. Unit checks cover travel bounds,
consumption, stopping and focus cleanup. Live qualification confirms horizontal/vertical steering and hits on moving
enemies. The final build has its own 20-launch artifacts; earlier launch batches
are retained as historical evidence.

Some exploratory screenshots came from a visible X11 window with physical user
input interleaving with injected input. The suspected menu-state desynchronization
from that session is unconfirmed. Further input qualification uses a private
Xvfb display and an independent save directory; it cannot receive physical
mouse events from the desktop.

## Final desktop controls and active soak

Final binary SHA-256: `5162e4c919a733a639b2266dffc12c3c88af524c15115c0ef5823c422f230913`.
Rust 1.94.1, GCC 16.1.1, CMake 4.4.1 were used locally. The final verification
run passed 55 ordinary library tests with one external-media test ignored;
the external supplied-intro test is checked separately by the movie ledger.

Mouse steering was verified against moving enemies in the opening hall. A
focus-loss capture shows aim and pad motion before loss, then normal move mode
and a neutral pad afterward; phone/pointer interaction works after recovery.
See target/qualification/controls/final. E invokes the shared native action icon;
without a nearby contextual action it enters native aim, so interactions should
be invoked when their corresponding icon is visible.

Space supplies alternating translational acceleration to escape grabs, while
R retains its verified gravity-only reload tilt. This follows the original
[Capcom control description](https://www.capcom.co.jp/ir/english/news/html/e90512.html).
A supplied-game grab was visibly released by holding Space; source waveform and
focus cleanup are also unit checked. The test helper originally warped the
pointer while simulating button presses; that moved relative aim unexpectedly.
The corrected helper presses buttons without motion, and combat then succeeded.
Ordinary game-over reloads during test-operator delays are not counted as host
faults or successful chapter qualification.

The final active-world soak has an independent observer under
`target/qualification/active-world`. It recognizes the HUD frame by fixed contrast
points, with reviewed positive world/aim captures and negative phone, pickup and
cutscene captures. Only adjacent positive observations no more than two seconds
apart count. Phone, inventory, pickup overlays, loading, title, cutscenes and
ordinary game-over screens are excluded. The input driver exercises movement,
turning, relative mouse aim, inventory and shake in the cleared opening hall;
it does not write the observer's result. Completion remains pending until
summary.json records at least 1,800 active seconds.

The standalone touch-mode volume-zero check is in
`target/qualification/standalone-muted-touch`. Its six-second visible intro
segment contained 589,824 samples, all zero. A separate tone routed explicitly
to the same private sink produced 47,926 nonzero samples (peak 262), validating
the monitor path. /proc independently showed empty child directories over both
the repository and T-REX and a cwd of /tmp. Natural playback logged Ended and
the process exited normally. This check used the prior mouse build; the resource,
volume, decoder and touch-mode implementations are unchanged in the final build.

## Loading optimization, 2026-10-16

Final release SHA-256: `8c153875a00d06daa9d19db8c5a5171e36c0ae757108714020e9930814595c84`.
The same binary ran two original-asset controls and three optimized runs,
including first cache creation, on a private Xvfb display with llvmpipe. All
runs used a disposable copy of the imported installation and saves. Existing
user runtimes and original imported files were not changed.

| Observation | Original control | Optimized |
|---|---|---|
| First level's visible Loading screen | 5.175–5.285 seconds | Not observed in all three runs |
| Movie skip completion to first native scene | 7.109–7.141 seconds | 2.017–2.108 seconds |
| Startup Loading screens, combined | 1.613–1.629 seconds | 0.881–0.967 seconds |
| Stable gameplay presentation | Median 16.67 ms | Median 16.66–16.68 ms; p95 17.02–17.15 ms |
| Full decoded asset cache preparation | Repeated ARM decoding | 0.384 seconds once, then verified reuse |

The median movie-to-scene wait fell from 7.125 to 2.018 seconds, about 72%.
The visible Loading label disappearing is not evidence of zero transition
time: fades and story presentation still take time. Logos, the menu camera,
movies and story dialogs were skipped using normal touch input in the test;
no clocks, game scheduling or frame limit were changed. The initial menu's
attract sequence still runs at its original speed when left unskipped.

The optimization serves a separately cached, uncompressed `main.dz` through
the read-only guest filesystem. Python's independent LZMA decoder verified
all 48 resources (18,546,804 decoded bytes) against the original archive and
rejected a one-byte tamper control. All decoded resources were also checked
to avoid compression-header signatures that could confuse this old SDK's
automatic stream detector. Archive reader flags are retained; changing them
to the stored flag described for newer Derbh versions does not work here.

A separate virtual `app.icf` profile raises `SerialiseCallbackBytes` from
10 KiB to 1 MiB, with `SerialiseCallbackMs=50`. This avoids repeated frame
waits while serializing large resources and keeps progress callbacks regular.
Both original files remain intact and installation verification still hashes
them. Cache files are tied to the original digest, verified on reuse, written
atomically and regenerated after corruption. Unrecognized archives or cache
I/O failures use the original loader. `REDEGPC_ORIGINAL_ASSETS=1` disables both
the decoded archive and loading profile for comparisons. `make dev` now uses
the optimized release build; `make debug` still builds for source debugging.

Each optimized run reached the actual gameplay HUD, moved Leon, opened the
pause/map screen and exited normally. The whole phone icon is matched to
identify gameplay: a corner-only HUD test produced a movie false positive
and was replaced before final measurement. Gameplay captures, timed logs,
samples and presentation traces are under
`target/qualification/startup/final-{original,cached}`. Recounted results are
in `target/qualification/startup/comparison.json`. `scripts/benchmark_loading.py` creates the live evidence;
`scripts/check_asset_cache.py` and `scripts/check_loading_benchmark.py`
independently check its asset, gameplay and timing results.

The locked release build, formatting, focused Clippy, CLI fixtures and all
60 enabled library tests pass (one pre-existing test remains ignored).
New tests cover malformed/truncated archives, size/dictionary limits,
out-of-order locations, exact decoded bytes, cache corruption/reuse, profile
repair, and redirecting read-only resources without affecting writable saves.
No vendor or locked dependency revision changed. This qualifies the measured
first-level loading improvement; the earlier campaign/chapter acceptance
requirements above remain separate.

## Desktop gameplay pacing correction, 2026-10-16

Release SHA-256: `bd74bd2cb8e43330161d68b2eaf667345a6eb86dd3d96964eefc6efe7e14243b`.
The desktop control reproduced 8.06–17.98 FPS in the game's EAGL context while
host presentation still ran around 60 FPS. Every OpenGL context now explicitly
requests immediate swaps: guest timers, EAGL and composition already impose
their own pacing, and blocking driver swaps stall the cooperative guest threads.
The compositor FPS counter also counts completed presentations rather than
run-loop checks that may skip rendering.

Two corrected runs on the normal X11 desktop with the Radeon RX 6700S and no
vblank environment overrides reached gameplay, moved Leon, opened pause and
exited normally. Their stable guest observations were 58.60–60.22 FPS. Median
presentation intervals were 16.667 and 16.661 ms, with p95 of 17.050 and
16.912 ms. The control executable differed only in omitting the explicit
swap-interval request; it retained the corrected compositor counter. All runs
used disposable installation/save copies. Real saves were not opened by them.

The loading benchmark now retains normal driver synchronization settings and
raises its window before pointer input. Earlier exploratory desktop captures
could be obscured by other windows, so they are not used for the final gameplay
comparison. Final artifacts are in `target/qualification/performance/fixed-native`
and `control-native-raised`, independently recounted by
`scripts/check_gameplay_performance.py`, including the slow control's game FPS.
The rebuilt binary passes formatting, focused Clippy, all 60 enabled library
tests and CLI checks; the existing external-media test remains ignored.

## Launcher and launch-time optimization, 2026-10-21

All changes are code-only; no artwork, texture, audio or game file changed.

The launcher now decodes its artwork once on four background threads,
starting with the Overview's images while the window opens. Rotated originals,
resampled pieces and finished page backgrounds are cached by window size, and
the other pages are drawn in the background once resizing settles. Every page
background was hashed before and after the change at 1440×810, 1100×700 and
1700×900, including achievement selections and filters: all 24 renders are
pixel-identical.

| Launcher action | Before | After |
|---|---|---|
| Open and first paint | ~650 ms | ~280 ms |
| Switch page (first visit and later) | 340–520 ms | 25–45 ms |
| Select or page achievements | ~45–65 ms | ~35–40 ms |

`redegpc check` and each launch hash the installation and the decoded asset
cache. SHA-256 now uses the x86 SHA extensions when the CPU has them, with the
portable rounds as fallback; a test compares both on 2,000 random blocks and
against an independent digest. The installation check fell from ~100 ms to
~28 ms, and launch to "CPU emulation begins" from ~404 ms to ~246 ms. The same
function also identifies HUD textures during level loads.

Every switch between the game's EAGL context and the compositor's context
refilled the global OpenGL function table, over a thousand `glXGetProcAddress`
lookups per switch on the emulator thread. GLX and EGL entry points do not
depend on the context, so on Linux the table is now filled once per process.
On the idle radio dialog after Continue, emulator-thread CPU fell from
0.19 to 0.12 cores (three alternating runs each, disposable data copies).

Profiling the Continue load found no remaining loading stall. With the
original archive, Continue spends 5.3 seconds on a black loading screen; with
the decoded cache that phase is gone. The remaining ~3.1 seconds are the
menu's own selection transition (~1.7 s) and the area title fade-in (~1.4 s),
during which guest-PC samples match the ordinary frame loop. Startup loading
runs behind the fixed-length Capcom and Airplay logos. Neither was shortened,
since that would change game timing.

The rebuilt binary passes `scripts/verify.py` (formatting, focused Clippy,
65 library tests with the existing one ignored, CLI fixtures). The launcher
suite passes up to its fullscreen-geometry check, which fails identically with
the previous launcher on this Wayland desktop.
