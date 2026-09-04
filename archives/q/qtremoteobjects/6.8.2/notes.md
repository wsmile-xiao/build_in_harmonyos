# qtremoteobjects 6.8.2 adaptation notes

## Build configuration
- Uses the `harmonyos-clang` Qt mkspec.
- Builds the two focused upstream POD test targets on OHOS.
- Disables examples, benchmarks, manual tests, and tests-by-default.
- Requires `qtbase/6.11.1` (cross-version adaptation: qtbase/6.8.2 is not available in the ohpcd Conan remote).
- Generates `VirtualRunEnv` for Qt shared-library execution.

## Adaptation strategy
- qtbase/6.8.2 is NOT available in the ohpcd Conan remote (only 6.11.1 exists).
- This recipe depends on `qtbase/6.11.1` with `transitive_headers=True` and `transitive_libs=True`.
- The test_package CMakeLists.txt uses `find_package(Qt6 6.11.1 ...)` to match the available Qt version.

## Source
- URL: `https://download.qt.io/official_releases/qt/6.8/6.8.2/submodules/qtremoteobjects-everywhere-src-6.8.2.tar.xz`
- SHA-256: `d02ad3ede11b0bbf8187cb79227383aed5b4538107b522d1249eab7b1b5eb629`
---

**编译结束**: 2026-09-04 03:30
**最终状态**: built
