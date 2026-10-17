# SEP 1.4.1 HarmonyOS PC adaptation notes

## Scope and source identity

- Package scope: the official standalone C API (`src/*.c`, `src/sep.h`) built by the upstream CMake project.
- Upstream release: SEP 1.4.1, a combined Python and C source distribution.
- Source SHA-256: `a0c8324ab66ee716080472cb212e4303e6c3e33b0d43763075b20d4cab793b25`.
- The Python/Cython wrapper is intentionally not packaged as part of this C/C++ task; its upstream suite was still executed as a source-baseline check.

## Language preflight

The release root contains a Python packaging manifest, five Python/Cython files, and the independent C library. The task boundary is the upstream `src/` C library: eight compiled C translation units were detected there, giving a 100% C result. This is compatible with the requested C/C++ migration family.

## Dependency preflight

SEP's standalone C library has no third-party build or runtime dependency. It links only the platform math library. The project preflight therefore reported no unpublished Conan dependency.

## Build adaptation

- Uses Conan's CMake toolchain and the compiler selected by the active profile.
- Sets `CMAKE_POLICY_VERSION_MINIMUM=3.5` because CMake 4 removed compatibility with the upstream `cmake_minimum_required(VERSION 2.6)` policy baseline.
- Defines `SEP_VERSION_STRING` as `1.4.1`, matching the downloaded release.
- Preserves the upstream shared-library build and installs `libsep.so` plus `sep.h`.
- Applies no source patch and injects no HarmonyOS platform macro.

## Upstream test inventory and execution

Three source-level test assets were found:

1. `ctest/test_image.c`: official C integration executable covering background estimation, source extraction, and aperture photometry.
2. `ctest/compare.py`: official catalog oracle comparing the C result with the bundled SExtractor reference.
3. `test.py`: 26 collected pytest cases for the separately distributed Python/Cython binding.

Baseline execution results were 26/26 for `test.py`, 1/1 for `test_image`, and 1/1 for the catalog comparison: 28/28 in total, 100%. The Conan build repeats both official C-library validation stages against the HarmonyOS AArch64 objects; both pass without modifying upstream tests.

## Added consumer coverage

- `test_sep.c`: 30 installed-library checks across version metadata, background estimation, aperture photometry, source extraction, ellipse conversion and process-wide configuration setters.
- `test_sep_errors.c`: invalid-datatype rejection and public error-message behavior.
- `test_sep_ohos.c`: HarmonyOS-specific compile-time `__OHOS__`, AArch64 ABI, double-image background and shared-library runtime checks.

The adapted validation set contains 31 cases: the 28 upstream cases plus three consumer cases. This is greater than the upstream measured count, and all 31 pass.

## Verification commands

```sh
conan create archives/s/sep/1.4.1 \
  -pr:h=ohos-aarch64-linux-cross -pr:b=linux-x86_64 --build=missing
python3 tests/run_all.py
zsh ci/conan/build_and_test.sh archives/s/sep/1.4.1
```

## Common merge-issue audit

- Exact package/version path and official HTTPS source URL are used.
- Source checksum matches the downloaded release.
- Only one version directory is changed; no framework, software-level, cache, archive, credential or generated build file is included.
- `test_package` calls real installed SEP APIs and contains a complete `MANIFEST.yml`.
- No test is skipped, weakened or modified, and no CI gate is bypassed.
- The package contains only a library, so software-level `commands.json` is not applicable.
