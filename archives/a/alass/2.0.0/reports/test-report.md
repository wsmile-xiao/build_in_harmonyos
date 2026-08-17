# alass 2.0.0 HarmonyOS test report

## Environment

- Local host: Windows; Python 3.12.10; Conan 2.29.1 for static inspection
- Target: HarmonyOS, `ohos-aarch64`
- Shadow runner: single-package device lock with isolated task directories
- Conan: 2.31.2
- Cargo/rustc: 1.97.1
- clang: 15.0.4

## W0 dependency result

- Conan library dependencies: none
- Git dependencies: none
- Bundled C dependency: `webrtc-vad`, built with Conan-selected clang
- Optional runtime dependency: FFmpeg/ffprobe for video references only
- Minimal subtitle-to-subtitle path: no FFmpeg dependency

Result: PASS. No separate dependency-library adaptation is required.

## Local checks

| Check | Result | Evidence |
|---|---|---|
| Source download and extraction | PASS | Official `v2.0.0` archive |
| Source SHA-256 | PASS | `ce88f92c7a427b623edcabb1b64e80be70cca2777f3da4b96702820a6cdf1e26` |
| Build-system analysis | PASS | Cargo workspace with `alass-core` and `alass-cli` |
| Upstream test audit | PASS | Three active tests; one commented-out occurrence excluded |
| Recipe syntax and YAML | PASS | Python AST and YAML structure checks |
| Conan recipe operations | PASS | Inspect, export, and source method |
| Text and change scope | PASS | UTF-8/LF; target version directory only |
| Project review | PASS | 12 PASS, 1 expected warning, 0 FAIL |

## Shadow CI result

- Run ID: `codex-unknown-lib-alass-2.0.0-2224-r8-20260816-150649-14297`
- Start: 2026-08-16 15:06:50 +0800
- End: 2026-08-16 15:16:54 +0800
- Exit code: 0

| Check | Result | Evidence |
|---|---|---|
| Main Cargo build | PASS | Locked release build completed in 2m20s |
| Main upstream tests | PASS | 3 discovered, executed, and passed; 0 failed/skipped |
| Conan package | PASS | `bin/alass-cli` and `LICENSE` packaged |
| Consumer smoke | PASS | 5 discovered and passed |
| Fresh-source upstream tests | PASS | Download, patch, build, and 3/3 tests in `test_package` |
| Destructive negative test | PASS | Tests confirmed to depend on the package |
| L0 | PASS | All quality gates passed |
| L1 | PASS | `test_package` executed with structured evidence |
| L2 | PASS | `alass-cli --version` succeeded |
| L4 | PASS | Patch scan clean |
| L5 | PASS | `bin/` contains the executable |
| Runner stderr | PASS | Empty |
| Device lock cleanup | PASS | Global lock free after exit |

The recipe emitted `HMBS_UPSTREAM_TEST_RESULT` with 3/3 passing. The consumer emitted `HMBS_TEST_PACKAGE_RESULT` with 5/5 passing and repeated the same upstream suite from a fresh source tree.

## Reviewed warnings

- L0k: software-level `archives/a/alass/commands.json` is missing. That path is outside this version-only issue; L0 still passes.
- Rust: upstream `nom 2.1.0` may be rejected by a future compiler. It passes with Rust 1.97.1.
- Network: one package-cache download warning recovered automatically.

## Result

PASS. Single-package HarmonyOS shadow CI completed build, upstream tests, Conan packaging, consumer tests, negative testing, and every emitted L0-L5 gate. No blocking issue remains for the alass 2.0.0 version-level adaptation.
