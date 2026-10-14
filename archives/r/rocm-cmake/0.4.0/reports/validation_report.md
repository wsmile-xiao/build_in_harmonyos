# Validation Report for rocm-cmake 0.4.0

## Environment
- Device: HarmonyOS PC (aarch64), 制品 `os=OHOS`, `arch=armv8`
- Compiler: clang 15.0.4 / clang++ 15.0.4
- CMake: 4.1.2
- Git: 2.45.2
- Build date: 2026-10-06
- Source: https://github.com/ROCm/rocm-cmake/archive/refs/tags/rocm-4.2.0.tar.gz
  (sha256 299e190ec3d38c2279d9aec762469628f0b2b1867adc082edc5708d1ac785c3b)

## Compilation
- Status: ✅ **Success** — `conan create . -pr:h=<repo>/ci/conan/profiles/ohos-aarch64 -pr:b=<同上>` 退出码 0
  （上游层 1 套件、test_package 层 2 均在同一 `conan create` 内执行通过）
- Verified by: `ohc-run.py conan-verify rocm-cmake 0.4.0` → **G0/G1/G2/G3/G4 全 PASS**（见 `reports/conan-verify-report.md`）
- package_type: `build-scripts`（无 lib/、无 bin/，依 R38 不写 commands.json）

## Test Execution

### Layer 1 — upstream official test suite (in `build()`)
- Command:
  ```
  ctest --output-on-failure -E 'pass-simple-soversion|pass-simple-soversion-env|pass-version-norepo|pass-version-parent'
  ```
- The upstream suite is driven by `test/test.cmake` and consists of
  `test/pass/*.cmake` (17) + `test/fail/*.cmake` (2) = **19 ctest cases**,
  each performing a real configure/build/install (not a stub).
- Note (why the recipe must quote the regex): Conan's `cmake.ctest()` joins
  `cli_args` into a **single shell string** executed via `sh` (there is no
  argv array), so the `-E` regex must reach ctest with literal single quotes
  (`-E '<regex>'`). Without quoting the shell treats `|` as a pipe, ctest
  receives only the first alternative and the remaining fragments are run as
  shell commands (measured **exit 127**). Repeating `-E` does **not**
  accumulate (measured `-E A -E B` → still 18 tests); a single quoted
  `-E 'A|B|C|D'` excludes exactly the 4 platform-limited cases → **15 tests**.
  This is the fix applied in `conanfile.py::build()`.

| Metric | Value |
|--------|-------|
| Total upstream cases | 19 |
| Passed (OHOS, measured) | 15 |
| Exempted platform-limited cases | 4 |
| Pass rate (executed) | 15/15 (100% of executed) |

#### Exempted cases — per-case root cause (TEST_QUALITY_SPEC §3.3 path 3)
1. `pass-simple-soversion`
   - Root cause: HarmonyOS/OHOS does not create the versioned `.so` symlink
     chain (`libsimple.so.1` is absent). A plain CMake project using
     `SOVERSION` shows the same behaviour on OHOS.
   - Impact: none — CMake installation and consumer linking work without the
     versioned symlink. Same exemption reason as the merged rocm-cmake 0.12.0.
2. `pass-simple-soversion-env`
   - Root cause: identical to (1) — the env-var variant of the soversion case.
   - Impact: none.
3. `pass-version-norepo`
   - Root cause: the upstream version test framework assumes git metadata
     resolvable from the test checkout. In a non-git (tarball) tree
     `git describe` fails and the expected value (0) does not equal the empty
     `PROJECT_VERSION_TWEAK`, plus `ROCMSetupVersion` uses `--match [0-9]*`
     while the test harness uses `--always` (inconsistent selection semantics).
   - Impact: none — only the version-tweak assertion is affected; the package
     version itself is a fixed source constant (0.4.0).
4. `pass-version-parent`
   - Root cause: same git-metadata assumption as (3).
   - Impact: none.

> The 4 cases are excluded **explicitly** with ctest `-E`; no upstream test
> file is modified and no case is silently skipped.

### Layer 2 — test_package (consumer, end-to-end)
- Command: `conan create` (runs `test_package/conanfile.py::test()`)
- Result: ✅ **8/8 assertions pass, exit code 0** — measured output:
  `OK: rocm-cmake 0.4.0 consumer test passed (ROCM_VERSION=0.4.0, PATCH=0, checksum=40)`
- What the consumer flow asserts (measured):
  - configure-time (4): `find_package(ROCM REQUIRED)`, `rocm_setup_version(VERSION 0.4.0)`
    == 0.4.0, `rocm_get_patch_version` == `ROCM_LIBPATCH_VERSION` ("0"),
    exported config `test_package-config.cmake` exists (else `FATAL_ERROR`)
  - install-time (2, executed because `build()` now calls `cmake.install()`):
    `librocm_consumer_core.a` and `lib/cmake/test_package/test_package-config.cmake`
    are actually installed by `rocm_install_targets` / `rocm_export_targets`
  - runtime (4): `test_package.cpp` re-parses the version, checks major.minor.patch
    == 0.4.0, checks patch field == "0", verifies the version checksum == 40 → exit 0

#### Layer 2 defects found by the real `conan create` (both fixed in this round)
1. **Macro-guard scope (build-blocking, 缺陷 1)** — `test_package.cpp` guarded
   `ROCM_CONSUMER_VERSION` / `ROCM_CONSUMER_PATCH` with `#error` for **every**
   translation unit, but those macros are only injected into the `test_package`
   **executable** target (`target_compile_definitions(test_package PRIVATE ...)`);
   the same source is also compiled into the `rocm_consumer_core` **library**
   target, which only defines `ROCM_CONSUMER_LIBRARY_ONLY`. The two `#ifndef`
   guards were placed **before** the `#ifdef ROCM_CONSUMER_LIBRARY_ONLY` branch,
   so the library TU necessarily hit `error: "ROCM_CONSUMER_VERSION must be
   defined ..."` + `error: "ROCM_CONSUMER_PATCH must be defined ..."`
   (`2 errors generated.`). Fix: wrap the two `#ifndef ... #error` guards in
   `#ifndef ROCM_CONSUMER_LIBRARY_ONLY ... #endif` so they apply only to the
   executable branch. The guards themselves are kept (useful self-check); no
   assertion was removed and no value is read from the environment.
2. **`build()` never called `cmake.install()` (验证未真正执行, 缺陷 2)** — the
   real-output assertions at the end of `test_package/CMakeLists.txt` live inside
   `install(CODE "...")` (they check that `librocm_consumer_core.a` and
   `lib/cmake/test_package/test_package-config.cmake` were actually installed by
   `rocm_install_targets` / `rocm_export_targets`). `test_package/conanfile.py::build()`
   only ran `cmake.configure()` + `cmake.build()`, so those assertions never
   executed ("claimed verified without verifying"). Fix: call `cmake.install()`
   right after `cmake.build()`, still inside the same
   `with env.vars(self).apply():` block. (The main recipe's `package()`
   `cmake.install()` is untouched.)

## Installation Verification
- Installed files:
  - `share/rocm/cmake/ROCMConfig.cmake`
  - `share/rocm/cmake/ROCMSetupVersion.cmake`
  - `share/rocm/cmake/ROCMInstallTargets.cmake`
  - `share/rocm/cmake/ROCMCreatePackage.cmake`
  - `share/rocm/cmake/ROCMPackageConfigHelpers.cmake`
  - `share/rocm/cmake/ROCMInstallSymlinks.cmake`
  - (+ ROCMChecks / ROCMAnalyzers / ROCMSetupVersion and the remaining modules)

## Conclusion
- **Layer 1** (upstream official suite, measured on OHOS): **15/19 pass**; the 4
  platform-limited cases (2 SOVERSION symlink + 2 git-metadata version) are
  explicitly exempted via ctest `-E` with documented per-case root causes — no
  upstream test file is modified and no case is silently skipped. The recipe
  passes the `-E` regex with literal single quotes so ctest receives it as a
  single argument (see the Layer 1 note; without quoting the shell mis-parses
  `|` and the build fails with exit 127).
- **Layer 2** (consumer `test_package`): the flow exercises the
  real `find_package(ROCM)` + `rocm_setup_version` / `rocm_get_patch_version` /
  `rocm_install_targets` / `rocm_export_targets` path end-to-end. The real
  `conan create` reached the library-target TU and initially **failed to build**,
  exposing two self-inflicted defects (缺陷 1 macro-guard scope; 缺陷 2 missing
  `cmake.install()`). Both were fixed and then **re-verified by a full local
  `conan create` run: 8/8 assertions pass, exit code 0**.
- **Recipe verification**: `ohc-run.py conan-verify rocm-cmake 0.4.0` →
  **G0/G1/G2/G3/G4 all PASS** (see `reports/conan-verify-report.md`).
- **Local CI simulation**: `ci/conan/setup.sh` + `ci/conan/build_and_test.sh
  archives/r/rocm-cmake/0.4.0` → **L0 pass, L1 pass** (L2 skip: no `bin/`;
  L4 pass; L5 warn: no artifacts), `Build Summary: Total 1 / Success 1 / Failed 0
  / Pass rate 100.0%` (log: `reports/w3-local-ci.log`).
- **Overall status**: `built` — all three verification layers replay green after
  the three defects (#5 `-E` quoting, #6 macro-guard scope, #7 missing
  `cmake.install()`) found by real local runs were fixed.
