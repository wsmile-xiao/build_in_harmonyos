# libkdcraw 26.04.0 notes

## Scope

This package provides `libKDcrawQt6.so` (CMake package `KDcrawQt6`,
imported target `KDcrawQt6`), the KDE RAW image decoding library wrapper
around LibRaw. Platform task #8242, branch `feat/libkdcraw-26.04.0`.

Upstream: https://invent.kde.org/graphics/libkdcraw, tag v26.04.0
(KDE Gear 26.04 line).

## Upstream build system (verified from the v26.04.0 tarball)

- Top-level `CMakeLists.txt`: `cmake_minimum_required(3.16.0)`,
  `find_package(ECM 6.0.0 CONFIG REQUIRED)` then KDEInstallDirs/
  KDECMakeSettings/KDECompilerSettings + ECMGenerateHeaders/
  ECMSetupVersion/CMakePackageConfigHelpers/ECMQtDeclareLoggingCategory/
  ECMGenerateExportHeader/ECMDeprecationSettings/FeatureSummary.
- `find_package(Qt6 6.5.0 REQUIRED NO_MODULE COMPONENTS Core Gui)`.
- `find_package(LibRaw 0.18 REQUIRED)` - resolved by the bundled
  `cmake/modules/FindLibRaw.cmake` (plain find_path/find_library; the
  PkgConfig prefix is opportunistic and absent on OHOS).
- `src/` builds the `KDcraw` library target: OUTPUT_NAME `KDcrawQt6`,
  EXPORT_NAME `KDcrawQt6`, SOVERSION 5, package name `KDcrawQt6`, empty
  CMake namespace. Public link: Qt6::Core/Qt6::Gui; private: LibRaw::LibRaw.
- `tests/` (BUILD_TESTING=ON): `raw2png` and `libinfo` executables - both
  are manual command-line tools, **never registered via add_test**, so the
  upstream ctest count is 0. This matches the upstream .gitlab-ci.yml which
  does not run ctest either.

## OHOS adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` (OHOS is not in the KDE platform list).
- ECM_MODULE_PATH + ECM find/kde-module paths are passed explicitly
  (CMakeDeps-generated ECMConfig doesn't propagate the variable).
- `conan_cmakedeps_paths.cmake` written manually: qtbase/libraw packages
  use cmake_find_mode=none, so CMakeDeps doesn't add their lib/cmake dirs
  to CMAKE_PREFIX_PATH. The file also seeds CMAKE_LIBRARY_PATH/
  CMAKE_INCLUDE_PATH so the module-mode FindLibRaw resolves.
- Qt6 found in CONFIG mode via the qtbase package's lib/cmake (NO_MODULE).
- No patches needed: all adaptations are option/variable level.
- Build-time smoke runs of the upstream tools (raw2png usage banner,
  libinfo capability dump) are executed on the build machine inside the
  build tree.

## Verification

OHOS `conan create` (ohos-aarch64 profile, clang 15, libc++, Release):

- Library builds and installs: `libKDcrawQt6.so` + `KDcrawQt6Config.cmake`
  + KDcrawQt6Targets.cmake + headers under include/KDcrawQt6/.
- Upstream tools built: `tests/raw2png`, `tests/libinfo` (BUILD_TESTING=ON).
- Upstream tool smoke runs (executed inside conan create, cwd=build/tests
  so the build-tree-relative `../bin/libKDcrawQt6.so` NEEDED resolves):
  - `libinfo`: `Libkdcraw version : "5.0.0"`, `Libraw version : "0.22.1"`,
    `Raw files version : 5`, 1258 supported cameras (LibRaw cameraList).
  - `raw2png` without args: usage banner (`Usage: <rawfile>`), exit -1 by
    design (upstream behavior). Nonexistent-file run: `Identify RAW image
    failed. Aborted...` - clean abort through the LibRaw identify path.
- `test_package`: 1/1 passed (consumer links KDcrawQt6 + Qt6, calls the
  KDcraw static metadata API, RawDecodingSettings/DcrawInfoContainer value
  types, and the decode-path rejection checks; offscreen platform).
  Output: `KDcraw version 5.0.0, LibRaw 0.22.1, 45 RAW extensions,
  1258 cameras` + `__OHOS__` macro check.
- Full reference:
  `libkdcraw/26.04.0#7beb1eaff53dcb08853368df9ac3b514:7238b6908645ddcc192eb785e781237c584b1412#ab97349dd4bc84cee23a0250d808d185`.

## Test registration notes (rule4 / upstream N)

- Upstream registers **0** ctest entries (no add_test anywhere in the
  26.04.0 tree; tests/CMakeLists.txt only adds two executables).
- The two upstream tools are still built (BUILD_TESTING=ON) and executed
  as smoke runs; their output is captured in the conan create log.

## Dependency closure

- qtbase/6.11.1 (Qt6 Core+Gui, CONFIG mode)
- libraw/0.22.1 (raw/raw_r + zlib/1.3.1.1 + libjpeg/10 transitively)
- ecm/6.26.0 (tool_requires)
- No KF6 framework library is required.
