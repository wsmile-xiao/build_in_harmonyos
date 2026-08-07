# adamstark-audiofile 1.1.4 Adaptation Notes

## Summary

- Upstream: https://github.com/adamstark/AudioFile
- Version: 1.1.4
- Source archive: https://codeload.github.com/adamstark/AudioFile/tar.gz/refs/tags/1.1.4
- Source SHA-256: `e3749f90a9356b5206ef8928fa0a9c039e7db49e46bb7f32c3963d6c44c5bea8`
- Build system: CMake
- Package type: header-library
- License: MIT
- Conan dependencies: none

## Upstream Tests

The upstream CMake project registers one CTest entry named `Tests`. The binary
uses doctest and reports 73 test cases. Host validation on 2026-08-06 used:

```bash
cmake -S <source> -B <build> -G Ninja -DBUILD_TESTS=ON -DBUILD_EXAMPLES=OFF -DCMAKE_BUILD_TYPE=Release
cmake --build <build> -- -j1
ctest --test-dir <build> --output-on-failure -V -j1
<build>/tests/Tests.exe --list-test-cases
```

Result: 73/73 doctest test cases passed, with 1,739,931 assertions passed.
Assertions are not counted as independent tests.

## Packaging

The recipe keeps the upstream CMake install path and disables examples. Upstream
tests remain enabled and are run during `conan create` when the package can be
executed in the active build context. The package exposes:

- CMake file name: `AudioFile`
- CMake target: `AudioFile::AudioFile`
- Include directories: `include` and `include/AudioFile`

## Patches

No source patch is required.

## W0 Dependency Gate

The recipe has no third-party Conan dependencies. A fresh isolated Conan home
was used with the OHOS/armv8 profile and `conan graph info --build=never`.

Result: graph node count 1, root reference `adamstark-audiofile/1.1.4`,
root `info_invalid` was `None`, and requirements were empty. Evidence is
recorded in `reports/w0-dependency-graph-20260806.md`.

## Consumer Test

The Conan `test_package` builds one independent consumer executable. It checks:

- WAV save/load through memory
- AIFF save/load through memory
- WAV save/load through the filesystem

This is counted as 1 independent added consumer test. Its internal checks are
assertions, not additional independent tests.

## HarmonyOS PC W3

Target-device validation on 2026-08-06 used
`currentUser@10.62.148.108:2222` for the complete run against recipe input
commit `55fc5857fa3ec35e8bba4a750a43b67255c6f9bd`. The W3 runner used a fresh
isolated Conan home, OHOS/armv8 host and build profiles, and single-job
build/test settings.

Result: `conan create` exited 0. The upstream CTest entry passed 1/1, the
consumer CTest entry passed 1/1, and the consumer executable printed
`PASS: adamstark-audiofile consumer round-trip checks passed`.

Evidence is recorded in `reports/harmonyos-pc-device-w3-20260806.md`.
