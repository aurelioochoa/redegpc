# redegpc implementation contract

Base: touchHLE ca1de89c578e79746f33c1332e28efd106c334ba, Linux x86_64, English jp.co.capcom.residentevil.en 1.03.00. Preserve runtime, submodules, notices and locked upstream versions. No game assets enter git.

Depth tree: application → import/runtime integration; movie playback; controls; qualification.

| ID | Outcome | Owner / paths | Needs | Gate |
|---|---|---|---|---|
| C1 | Safe atomic versioned import, SHA-256 manifest, encrypted/unsupported rejection, immutable source resources | root: src/redegpc/**, src/redegpc.rs | none | G2 |
| C2 | Default Rust CLI import/check/run/help, XDG settings/saves/logs, typed cwd-independent runtime entry | root: Cargo.toml, src/lib.rs, src/paths.rs, src/log.rs, docs/**, scripts/** | C1 | G1,G3 |
| C3 | FFmpeg local movie playback with audio/frame presentation, skip/failure/completion on guest event thread | movie: src/frameworks/media_player/**, src/window/movie.rs | none | gates/movie.md |
| C4 | Game action layer WASD/arrows/RMB motion/LMB/R/Space shake/E/Tab/Escape, touch mode, focus clearing | controls: src/redegpc_controls.rs, src/window.rs, src/options.rs | none | gates/controls.md |
| C5 | Baseline then twenty menu launches, actual intro and input gameplay | root: docs/qualification.md | C1-C4 | G4,G5 |
| C6 | Thirty minutes, first chapter/transition, save/reload | root: docs/qualification.md | C5 | G6 |
| C7 | Release build locked, formatting, focused Clippy/tests, retained licensing | root: notices/docs/build and integration | C1-C4 | G1,G7 |
| C8 | External drive independent launch, frame pacing/loading/screenshot evidence and defects | root: docs/qualification.md | C1-C4 | G3,G8 |

Interfaces: typed RuntimeConfig owns absolute app/resources/data paths plus GameSettings. Options gets redegpc_controls: bool (default false); root enables it in typed launch. Controls module remains separate from guest runtime. Movie implementation uses existing window/context and run loop; no worker may invoke guest callbacks. Movie window helper lives at src/window/movie.rs and is registered by controls owner in window.rs (coordinate). Preserve upstream behavior when game options disabled. No scheduling changes without traces.

Execution: independent movie and controls leaves use native agents after ownership claims. Root handles importer and runtime. Four passes per leaf: implement, expert review, defect hunt, polish; every returned check is reverified. No fabricated gameplay evidence. Qualification must record observed blockers.
