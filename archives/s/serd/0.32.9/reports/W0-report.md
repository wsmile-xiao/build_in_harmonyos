# serd 0.32.9 W0 dependency and feasibility report

## Decision

- Adaptation class: B, delivered as Path A (base adaptation) plus Path B (knowledge extension).
- Feasibility: passed. The pinned source is a small Meson-based C library with no third-party Conan dependencies.
- Package boundary: only `archives/s/serd/0.32.9/` is required for this adaptation.

## Upstream identity

| Item | Value |
|------|-------|
| Project | serd |
| Recipe version | 0.32.9 |
| Upstream commit | `0317806d56f9288294183b41074a6fd50a924f5a` |
| Version evidence | The pinned commit's `meson.build` declares `0.32.9` |
| Source archive | Official GitLab commit archive |
| Archive size | 380829 bytes |
| SHA-256 | `4cec57d40ff913a4530043ffc6e37f80b758f08fb807ac8d73b832d31f336a78` |

Upstream does not publish a stable release archive for this odd development version, so the recipe pins the exact official commit and verifies its archive hash.

## W0 dependency result

| Dependency type | Result | Evidence and handling |
|-----------------|--------|-----------------------|
| Conan requirements | None | The source and recipe require no third-party package. |
| zix | Not applicable | The pinned source contains no zix reference. The zix requirement in the historical `0.32.9-git` draft belongs to a different snapshot. |
| System libraries | `libm` | Meson detects the math library; the Conan package exposes `m` for Linux/OHOS consumers. |
| Build tools | Meson, Ninja | Available in the device runner environment. |
| Consumer-test tool | CMake | Available as `/data/service/hnp/bin/cmake`; that directory must be prepended to the runner PATH. |
| OHOS toolchain | Clang 15 | `/data/service/hnp/bin/clang` and `clang++` target `aarch64-unknown-linux-ohos`. |

No dependency library needs to be split into a separate adaptation PR.

## Build-system assessment

- Upstream uses Meson and builds the `serd-0` library plus the `serdi` command-line tool.
- Static linkage is the recipe default to reduce target loader and shared-library signing risk.
- Upstream checks and tools remain enabled; documentation and lint-only targets are disabled because they are not runtime requirements.
- Conan's Meson native/cross files need the OHOS `llvm-ar` and `llvm-ranlib` paths injected so static archives use the target toolchain.
- The packaged `serdi` executable is re-signed with the OHOS binary signing tool before the consumer test executes it.
- OHOS Meson test commands launch upstream Python scripts through the discovered interpreter instead of relying on archive executable bits.

## Test plan and result

Upstream registers 65 Meson tests:

| Group | Count |
|-------|------:|
| Header warning test | 1 |
| C unit tests | 8 |
| `serdi` command/input/I/O tests | 33 |
| Data-driven RDF suites | 23 |
| **Total** | **65** |

The Conan `test_package` adds two consumer-level checks:

1. Compile and run a C API test against the packaged library.
2. Run packaged `serdi` to convert Turtle input to N-Triples and verify the output.

All 65 upstream registrations and both consumer checks passed. The OHOS-only Meson command rewrite changes how four Python scripts are launched; it does not modify their bodies, arguments, fixtures, expected outcomes, or registration count.

## Risk register

| Risk | Level | Mitigation |
|------|-------|------------|
| Development version has no release tarball | Medium | Pin the exact official commit and SHA-256. |
| Meson chooses a host archiver | Medium | Inject OHOS `llvm-ar` and `llvm-ranlib`. |
| Python tests retain non-executable `0750` mode | Medium | Launch the four scripts through Meson's discovered Python interpreter. |
| Packaged CLI cannot execute unsigned | Medium | Remove any old code-sign section and self-sign `serdi`. |
| CMake is outside the default runner PATH | Medium | Prepend `/data/service/hnp/bin` for the heavy runner. |
| Device-global build contention | Operational | Use the isolated runner with `--try-lock`; exit 75 is resource contention, not a serd failure. |

## Validation evidence

- Windows preflight: source download/hash, recipe syntax, structured YAML, Conan 2.29.1 inspect/export/source, line endings, and atomic-scope checks passed.
- HarmonyOS device preflight: isolated `CONAN_HOME` with OHOS settings; runner-executed `conan graph info` passed with `OHOS 6.0`, `armv8`, Clang 15, static options, and no dependencies.
- HarmonyOS heavy shadow CI: runner `codex-serd-serd-serd-0.32.9-483c5112-conan-r6-20260821-212504-56435` ended `rc=0`.
- Upstream result: 65/65 passed, comprising 41 normal successes plus 24 expected-failure successes.
- Adapted result: 2/2 passed; L0, L1, L2, L4, L5, destructive negative testing, package artifacts, and the single-package build summary all passed.
