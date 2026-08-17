# Local validation

- Date: 2026-08-17
- Scope: Windows host preflight only; no device or shadow CI slot used.

## Completed

- Branch/worktree isolation confirmed.
- Official tag metadata and authoritative source mirror checked.
- Source archive downloaded and SHA256 verified.
- Source archive extracted successfully.
- Autotools/bootstrap, AVR GCC/Binutils dependency and multilib layout analyzed.
- Upstream tests counted: 462 sources in 17 categories.
- Conan recipe and substantive AVR consumer compile/link test prepared.

## Recipe checks

- Python AST parsing: pass for both Conan recipe files.
- YAML parsing: pass for conandata, manifest and test manifest.
- `conan inspect`: pass with OHOS-adapted Conan 2.29.1.
- `conan source`: pass; URL, SHA256 and `strip_root` extraction verified.
- `conan export avr-libc/2.2.1@ohpcd/stable`: pass.
- OHOS host/build profile graph: expected block at `avr-binutils/2.43.1`, which is absent from `ohpcd`.
- Exact remote query also confirms `avr-gcc-bootstrap/14.2.0` is absent.

## Not run

- `conan create`: unavailable until required AVR tool packages are published.
- Upstream compile/link subset: unavailable without AVR GCC/Binutils.
- Full simulator suite: unavailable without avrtest/simulavr.
- True-device/shadow CI: intentionally not queued in this front-preparation round.
