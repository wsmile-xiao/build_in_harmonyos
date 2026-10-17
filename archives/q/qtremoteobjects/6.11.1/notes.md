# qtremoteobjects 6.11.1 adaptation notes

## Build configuration

- Uses the `harmonyos-clang` Qt mkspec.
- Builds the two focused upstream POD test targets on OHOS. Their target-side
  `repc` code generator and CTest executables now run inside Conan's generated
  `VirtualRunEnv`, so Qt shared-library paths are present during both header
  generation and test execution.
- Disables examples, benchmarks, manual tests, and tests-by-default.
- Requires `qtbase/6.11.1`.
- Generates `VirtualRunEnv` for Qt shared-library execution.

## Verification

- Upstream Qt Test functions: 0/5 verified on the last authoritative OHOS run;
  Build #13295 stopped while `repc` was generating test headers because the
  loader could not resolve `libQt6Core.so.6` and Qt symbols. The next run will
  retry all five functions with `VirtualRunEnv` applied to the CMake target.
- Added consumer test: 1/1 (100% target, 17 assertions).
- Current Build #13295 reached qtremoteobjects build/test and failed while
  invoking upstream test helper generation. No success rate is claimed until
  the complete test targets and consumer package pass in official CI.

## Source

- URL: `https://download.qt.io/official_releases/qt/6.11/6.11.1/submodules/qtremoteobjects-everywhere-src-6.11.1.tar.xz`
- SHA-256: `40629895c69531a687a9c0258316cee3f04c2d18b2bf2ad36dc83e76a58f111a`
