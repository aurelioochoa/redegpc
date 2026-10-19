# Contributing to redegpc

**English** · [Español](CONTRIBUTING.es.md)

`redegpc` is an experimental Linux PC port of Resident Evil Degeneration, based on touchHLE. This guide covers contributions to this fork. Reports and changes are reviewed through this repository's [issues](https://github.com/aurelioochoa/redegpc/issues) and [pull requests](https://github.com/aurelioochoa/redegpc/pulls).

## Scope

The current target is **Linux x86_64** and the **English iPhone v1.03.00** release, bundle `jp.co.capcom.residentevil.en`. Contributions to the host, importer, controls, launcher, loading, saves, documentation and tests are useful.

General compatibility with other iPhone applications is outside the current scope. Read the [README](README.md), [launcher guide](launcher/README.md) and [observed results and limitations](docs/qualification.md) before describing a problem.

## Reports and proposals

Open an [issue](https://github.com/aurelioochoa/redegpc/issues/new/choose) in English or Spanish and include:

- Your `redegpc` revision (`git rev-parse HEAD`), Linux distribution and architecture.
- GPU/driver and desktop session when the problem concerns rendering, window behavior or input.
- Reproduction steps, expected and observed results, and whether an earlier revision worked.
- Game version, the result of `make check-game` and relevant logs. Do not attach the IPA or extracted game files; remove private details from logs.

For larger proposals, explain the problem and intended design to help review. Distinguish build/component checks from real gameplay observations; reaching the menu does not establish full campaign compatibility.

## Development setup

To submit changes, fork this repository on GitHub, clone your fork and create a branch from `main`. Follow the [README requirements and setup](README.md#requirements), retaining `Cargo.lock` and pinned submodules.

```sh
git submodule update --init --recursive
make setup
make build
```

The launcher needs Python 3.10+, Tk and Pillow; FFmpeg plays the original intro. Synthetic checks need no game files. Real-game checks require your own compatible, unencrypted IPA and a graphical desktop.

## Changes and verification

Keep each pull request focused on one problem and add tests when they catch a meaningful regression. Preserve imported originals and saves; use synthetic fixtures or isolated installations for tests. Follow the [existing coding style](dev-docs/code-style.md).

| Command | Purpose |
| --- | --- |
| `make fmt-check` | Check Rust formatting |
| `make check` | Check the library and binaries without linking |
| `make test` | Run library tests without the upstream iOS test toolchain |
| `make lint` | Run focused Clippy checks |
| `make test-cli` | Exercise the CLI/importer with synthetic fixtures |
| `make verify` | Check, build and run formatting, focused Clippy, library and synthetic CLI tests |
| `make test-launcher` | Run isolated launcher checks; requires a graphical display |
| `make check-game` | Verify your imported game installation |

Run `make verify` for runtime, importer or build-system changes. Add `make test-launcher` for launcher changes. For documentation, check links, examples and formatting; a runtime rebuild is unnecessary. State what you checked and identify any checks you could not run.

## Pull requests

Target **`aurelioochoa/redegpc:main`**. Describe the problem, resulting behavior, verification and any remaining limitations or regressions. Include screenshots when they help review visual changes. The maintainer reviews changes on GitHub; Gerrit and touchHLE review identifiers are not part of this fork's workflow.

## AI assistance

AI-assisted contributions are allowed in this fork. Contributors remain responsible for understanding and reviewing the content, verifying its behavior, and checking its provenance and license compatibility. Describe substantial AI assistance in the pull request.

This policy applies to `redegpc`. Changes submitted to upstream touchHLE must follow upstream's own contribution rules.

## Provenance and licensing

Contribute only material you have the right to share. Prefer public documentation, reproducible observations and original work; do not include copied proprietary code, leaked material, IPAs or extracted game assets. Follow the [piracy policy](CODE_OF_CONDUCT.md).

Preserve license and copyright headers, dependency notices and attribution history. Changes to MPL-covered code remain subject to its terms. New host code currently follows MPL-2.0; components retain their own licenses and the documented combined binary is GPL-3.0-or-later. See [LICENSE](LICENSE), [project notices](NOTICE.redegpc.md) and [upstream terms](README.touchHLE.md#license). Changing these contribution instructions does not change the software licenses.
