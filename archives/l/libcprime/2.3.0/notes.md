# libcprime 2.3.0 Adaptation Notes

## Overview

libcprime is a shared library for CoreApps (CoreBox, CoreFM, CorePad, etc.).
It provides utility functions for file management, bookmarks, themes, MIME handling,
and application dialogs using Qt Widgets.

- **Upstream**: https://github.com/rahmanshaber/libcprime
- **License**: LGPL-2.1-or-later
- **Build system**: Originally QMake (.pro), adapted to CMake via patch
- **Dependencies**: qtbase/6.11.1 (transitive_headers=True, transitive_libs=True)

## Adaptation Process

### 1. QMake to CMake Conversion (Patch 0001)

The upstream project uses a `libcprime.pro` QMake file. A new `CMakeLists.txt` was
created via patch `0001-add-cmake-build.patch` to enable CMake-based builds:

- Project configuration with Qt6 Core, Gui, Widgets components
- AUTOMOC and AUTOUIC enabled for Qt meta-object and UI compilation
- All 15 source files and 17 headers included
- bookmarkdialog.ui processed via CMAKE_AUTOUIC
- Library installed to `lib/` with headers to `include/cprime/`
- Theme files (.qss, .ini) installed to `share/coreapps/theme/`
- Docs and LICENSE installed

### 2. Qt6 Compatibility Fixes (Patch 0002)

Four Qt5-to-Qt6 API migration issues were fixed:

| File | Issue | Fix |
|------|-------|-----|
| stringfunc.cpp | `QFontMetrics::width()` deprecated in Qt6 | `horizontalAdvance()` |
| bookmarkmanage.cpp | `QList::toSet().toList()` removed in Qt6 | `QSet<QString>(list.begin(), list.end()).values()` |
| mimeutils.cpp | `QString::sprintf()` deprecated in Qt6 | `QString::section()` |
| applicationdialog.cpp | `QDir` constructor with `nullptr` sort parameter fails in Qt6 | `QDir::SortFlags()` |

### 3. OHOS Shared Library Configuration

The conanfile.py `generate()` method configures OHOS-specific shared library flags:
- CMAKE_SHARED_LIBRARY_SONAME_*_FLAG for proper soname
- CMAKE_SHARED_LIBRARY_RUNTIME_*_FLAG for rpath
- CMAKE_BUILD_RPATH_USE_ORIGIN for relative rpath

### 4. ELF Signing

All installed ELF binaries (shared libraries) are signed using `binary-sign-tool`
during the `package()` step when building for OHOS. This is required for code
execution on HarmonyOS PC.

## Verification

```bash
conan create archives/l/libcprime/2.3.0/conanfile.py \
  -pr:h=$SKILL_ROOT/ci/conan/profiles/ohos-aarch64 \
  -pr:b=$SKILL_ROOT/ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

The test_package creates a minimal consumer that:
1. Includes `cprime.h`
2. Creates a `QCoreApplication`
3. Calls `CPrime::Variables::CC_CoreApps_ConfigDir()` and `CC_CoreApps_BookMarkFile()`
4. Checks `CPrime::AppsName` enum values
5. Returns 0 on success

## Known Limitations

- The source URL uses a branch archive (master) rather than a tagged release, as
  upstream does not publish version tags. The sha256 is pinned for reproducibility.
- Theme file paths are hardcoded to `/usr/share/coreapps/theme/` in the source via
  a preprocessor define; the CMake install places them in the Conan package.
---

**编译结束**: 2026-08-25 01:09
**最终状态**: built

