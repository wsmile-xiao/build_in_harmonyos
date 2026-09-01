# libcprime

## Description

A library for CoreApps (CoreBox, CoreFM, CorePad, etc.) providing utility functions
for file management, bookmarks, themes, MIME handling, and application dialogs.

## OHOS Adaptation

- Converted from QMake (.pro) to CMake via patch (0001-add-cmake-build.patch)
- Fixed 4 Qt6 API compatibility issues via patch (0002-qt6-compat.patch)
- ELF signing applied for HarmonyOS PC shared libraries
- Qt6 cmake paths injected via conan_cmakedeps_paths.cmake

## Dependencies

- qtbase/6.11.1 (transitive_headers=True, transitive_libs=True)

## Reference

- Upstream: https://github.com/rahmanshaber/libcprime
