# kleidiai 1.19.0 adaptation notes

## Source

- Upstream: https://gitlab.arm.com/kleidi/kleidiai
- GitHub mirror: https://github.com/ARM-software/KleidiAI
- Release: `v1.19.0` (published 2026-03-30)
- Source archive: `kleidiai-v1.19.0-src.tar.gz`
- SHA256: `c50afd97e130f2f68f6adabb881696e410e1b57147dce87443dcd3bba012b287`

## Overview

KleidiAI is an open-source library of optimized performance-critical
micro-kernels (packing, matrix multiplication, quantization, depthwise
convolution) for AI/ML inference on Arm CPUs. It targets AArch64 only and
relies on Arm ISA extensions (Neon/FP16/DotProd/I8MM/BF16/SVE/SME/SME2).

Key properties:

- No external runtime library dependencies.
- No dynamic memory allocation, memory management, or scheduling.
- Stateless, stable C API (`kai_common.h` plus per-micro-kernel `.c`/`.h`
  pairs and GAS `.S` assembly variants).

## Build system

- Primary build system: CMake (`cmake_minimum_required(VERSION 3.16)`).
- `add_library(kleidiai)` builds a static library with C99 + C++17.
- Architecture features are selected with per-source `-march=armv8.x-a+...`
  compile options; non-MSVC builds use the GAS `.S` assembly variants.
- `install(TARGETS kleidiai EXPORT KleidiAITargets ...)` plus
  `install(DIRECTORY kai ...)` produce a `find_package(KleidiAI)` package
  exporting target `KleidiAI::kleidiai`.

## HarmonyOS adaptation notes

- The compiler defines `__linux__` (triplet `aarch64-linux-ohos`), so the
  CPU-feature detection path in `test/common/cpu_info.cpp` uses
  `getauxval(AT_HWCAP/AT_HWCAP2)`, which HarmonyOS musl provides
  (`sys/auxv.h` + `getauxval`). No source patch is required for this.
- Verified on the target device (20-core AArch64, CPU part 0xd42):
  `AT_HWCAP` exposes `asimd`, `asimdhp` (FP16), `asimddp` (DotProd), `sve`;
  `AT_HWCAP2` exposes `i8mm`, `bf16`. `sme`/`sme2` are not present, so the
  SME/SME2 tests are skipped by the upstream framework (expected).
- No patch is applied to the KleidiAI sources. The recipe builds the upstream
  CMake project unchanged.
- One build-time workaround is applied to the *test framework only*: HarmonyOS
  mounts `/tmp` read-only, but googletest's `CapturedStream` hard-codes
  `/tmp/` for its per-test capture files, so any test that writes to stdout
  aborts with `Failed to create tmp file /tmp/gtest_captured_stream.XXXXXX`.
  `_patch_gtest_tmpdir()` rewrites that path to a writable folder inside the
  Conan build directory before compiling the tests. The packaged library is
  unaffected.

## Dependencies

- Runtime Conan dependencies: none.
- Build-only tooling: CMake >= 3.18, clang >= 11.
- Test framework: GoogleTest 1.17.0, bundled as
  `third_party/googletest-v1.17.0.zip` and fetched locally by CMake
  `FetchContent` (no network access required).

## Test inventory

- Upstream tests are GoogleTest suites, one executable per source file plus a
  monolithic `kleidiai_test` executable, all registered with CTest via
  `gtest_discover_tests(... DISCOVERY_MODE PRE_TEST)`.
- Non-MSVC test source files (19):
  `bfloat16_test`, `buffer_test`, `float16_test`, `imatmul_test`,
  `dwconv_test`, 12 `matmul_clamp_*_test`, `matmul_test`,
  and `test/nextgen/tests/matmul_test_next.cpp`.
- The recipe runs the full suite with
  `ctest --test-dir <build-folder> --output-on-failure`.

## Verification

- Windows host: source/package are aarch64-only, so `conan create` cannot run
  natively on x86_64; recipe/Python/YAML static checks were run locally
  (`ast.parse`, YAML load, `git diff --check` all pass).
- HarmonyOS PC shadow CI (20-core AArch64, clang 15.0.4, cmake 4.1.2):
  - L0 quality gate: pass.
  - L1 (upstream tests + test_package): pass.
  - L2 (bin smoke): skip — static library has no `bin/`.
  - L4 (static scan): pass — no patches.
  - L5 (artifact): pass — `lib/libkleidiai.a` present.
  - Upstream GoogleTest suite (monolithic `kleidiai_test`, single process):
    `58385` tests from `42` suites ran in ~59 s — `22203` passed,
    `36182` skipped (SME/SME2 and other unsupported-feature cases),
    `0` failed.
  - Consumer test: `10/10` assertions passed.
