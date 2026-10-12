# qt5-qtgamepad 5.15.2 Build Notes

## Source
- Official Qt mirror: qtgamepad-everywhere-src-5.15.2.tar.xz
- sha256: c77611f7898326d69176ad67a9b886f617cdedc368ec29f223d63537d25b075c
  (download.qt.io 与 mirrors.tuna.tsinghua.edu.cn 双源下载逐字节一致)

## Build System
- qmake (Qt5 addon module, not CMake)
- Uses qt5-qtbase/5.15.2.2 from Conan artifact repo

## Key Adaptation Points
1. **qt5-qtbase path fix**: The qt5-qtbase Conan package ships .pri files
   that point to stale conan build directories; the recipe builds a
   private writable Qt prefix (symlinks + rewritten mkspecs) and runs
   qmake from it (qt5-qtsvg/qtwebsockets pattern).
2. **Stripping prevention**: QMAKE_STRIP="" is used because the OHOS
   loader rejects stripped ELF files (qmake's strip --strip-unneeded
   breaks the dynamic symbol table).
3. **No source modifications needed**: qtgamepad builds cleanly on
   HarmonyOS with the linux-clang mkspec (`patches_applied` is empty).

## Backend selection
- **evdev**: built (qtbase enables the evdev feature;
  `plugins/gamepads/libevdevgamepad.so` is packaged). Uses
  QtDeviceDiscoverySupport private headers + linux/input.h — both
  available in the qt5-qtbase package.
- **sdl2**: feature off — its configure.json probe requires
  pkg-config sdl2 which is not part of the declared dependency set
  (expected, no SDL2 in the CI worker environment).
- **QML import (src/imports)**: skipped automatically — qtbase does
  not provide the qml/quick modules (`qtHaveModule(quick)` is false).

## Upstream auto tests (rule4 — real counts)
qtgamepad 5.15.2 ships **no QTest suites** (`tests/auto/auto.pro` has
an empty SUBDIRS). The only upstream-registered automated test is
`tests/auto/cmake` (ctest_testcase):
- `qmake cmake.pro && make check` drives cmake configure + ctest;
- ctest registers exactly **1** test (`module_includes`): a
  `cmake --build-and-test` sub-project that does
  `find_package(Qt5Core/Qt5Gui 5.0.0 REQUIRED)` (the gamepad module
  dependency closure), compiles `module_includes_exe` and runs it;
- The upstream CMakeLists declares `cmake_minimum_required(2.8)`;
  host CMake 4.x needs `CMAKE_POLICY_VERSION_MINIMUM=3.5` exported for
  the whole check run (nested build-and-test inherits it);
- Verified in build(): "100% tests passed, 0 tests failed out of 1".

## Environment-limited behaviour (documented)
- The OHOS PC host has no physical gamepad (no /dev/input/js*
  device), so live gamepad-event behaviour is **environment-excluded**;
  `QGamepadManager` falls back to the dummy `QGamepadBackend`,
  `connectedGamepads()` is empty and `QGamepad` exposes its
  construction defaults. Consumer-side assertions (58 checks in
  test_package/test.cpp) cover this reachable API logic surface plus a
  QPluginLoader contract check of the packaged evdev plugin
  (dlopen + IID "org.qt-project.Qt.Gamepad.QtGamepadBackendFactoryInterface.5.9"
  + metadata Keys contains "evdev").

## Build Steps
1. conan install qt5-qtbase (from artifact repo)
2. Build private writable Qt prefix mirroring the qtbase package
3. qmake qtgamepad.pro -spec linux-clang
4. make -j2 QMAKE_STRIP=""
5. Upstream cmake test: qmake tests/auto/cmake/cmake.pro && make && make check
6. Package: lib, include, mkspecs, plugins (gamepads), cmake configs

## Build Artifacts
- lib/libQt5Gamepad.so.5.15.2 — main gamepad library
- plugins/gamepads/libevdevgamepad.so — evdev backend plugin
- include/QtGamepad/ — public headers
- lib/cmake/Qt5Gamepad/ — CMake config files (qmake-generated)
- mkspecs/modules/qt_lib_gamepad*.pri — qmake module configs

**编译结束**: 2026-10-06
**最终状态**: built
