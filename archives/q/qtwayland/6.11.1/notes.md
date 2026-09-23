# qtwayland 6.11.1 — Adaptation Notes

## Overview
Qt Wayland module providing Qt6 Wayland client and compositor libraries.

## Dependencies
- **qtbase/6.11.1.2**: Qt6 Core, Gui, OpenGL, DBus components (required)
- **wayland/1.22.0**: Wayland protocol libraries + wayland-scanner binary (required)
- **wayland-protocols/1.36.1**: Wayland protocol XML files (required)

## Key Adaptation Points

### 1. Platform Detection (OHOS → Linux)
CMake has no `Platform/HarmonyOS.cmake`, so `CMAKE_SYSTEM_NAME=HarmonyOS` causes
shared-library SONAME/versioning rules to not be applied. Presenting the platform
as Linux via a custom toolchain block enables the standard platform rules. The
OHOS clang driver still targets aarch64-unknown-linux-ohos.

### 2. Pkg-config Fix for Wayland Packages
The shipped wayland `.pc` files have `prefix=/` (root filesystem), which prevents
CMake's `FindWayland` from locating headers, libraries, and the scanner binary.
At `generate()` time, corrected `.pc` copies are written to the Conan generators
folder with proper `prefix=<conan_package_folder>`. This covers:
- `wayland-scanner.pc`: points to actual scanner binary
- `wayland-client.pc`, `wayland-server.pc`, `wayland-cursor.pc`: correct lib/include paths
- `wayland-protocols.pc`: correct share path for protocol XML files

### 3. ELF Signing
All installed ELF executables and shared objects are self-signed using
`binary-sign-tool` so the OHOS loader permits execution.

### 4. SONAME Symlinks
HMDFS breaks relative symlinks during install. The `_ensure_soname_symlinks()`
method recreates `.so` → `.so.6` → `.so.6.11.1` symlinks as needed.

## Upstream Tests
The upstream source registers 2 auto test targets via `qt_internal_add_test`
(52 QtTest case functions in total, matching the reviewer's full-run ctest
counting):
- `tst_client_iviapplication` (tests/auto/client/iviapplication): 3 case
  functions (createDestroyWindow, configure, uniqueIviIds)
- `tst_compositor` (tests/auto/compositor/compositor): 49 case functions

Both test targets are now BUILT and EXECUTED natively on the local
HarmonyOS PC (aarch64) host:
- `QT_FEATURE_wayland_server=ON` is enabled — qtbase/6.11.1.2 ships
  `libexec/qtwaylandscanner` plus the `Qt6WaylandScannerTools` CMake
  package, so the compositor module (and tst_compositor) builds in this
  standalone configuration.
- `libxkbcommon/1.6.0` is a new direct requirement: the keyboard test
  cases (simpleKeyboard, keyboardKeymaps, keyboardLayoutSwitching) only
  compile when QT_FEATURE_xkbcommon is on; XKB::XKB resolves via the
  relocated xkbcommon.pc.
- tst_compositor uses plain QTEST_MAIN + QGuiApplication and runs with
  QT_QPA_PLATFORM=offscreen (it creates its own in-process wl_display
  server side). tst_client_iviapplication forces QT_QPA_PLATFORM=wayland
  and connects to its in-process mock compositor through the ivi-shell
  plugin built in this tree.
- Environment required for a native run: XDG_RUNTIME_DIR on a SHORT
  path (108-byte Unix socket sun_path limit; the conan build folder is
  too deep), XKB_CONFIG_ROOT pointing at qtbase's share/X11/xkb,
  TMPDIR on a writable path (the upstream mock client hardcodes
  /tmp/wayland-shm-XXXXXX for its shm buffers which is read-only on
  OHOS — patched to honor TMPDIR).

Local full-run result (ctest, all registered cases):
- tst_client_iviapplication: 5/5 executed cases passed (3 upstream case
  functions + QtTest auto initTestCase/cleanupTestCase hooks), 308ms
- tst_compositor: 53/53 executed cases passed (49 upstream case
  functions incl. 5 data-driven viewportProtocolErrors rows + auto
  hooks), 1014ms
- ctest summary: 2/2 test targets Passed, 0 failed; 58/58 executed
  case items 100%

## Patch
- `0001-tst-compositor-use-tmpdir-for-shm-buffers.patch`: the upstream
  mock client's ShmBuffer creates its pool with mkstemp on the
  hardcoded /tmp/wayland-shm-XXXXXX. /tmp is read-only on HarmonyOS,
  so every buffer-backed case failed. The patch reads TMPDIR instead
  (falling back to /tmp), matching the platform temp convention.

## Build Configuration
- Build system: CMake (Qt Build System / qt_internal)
- Qt6 features: wayland_client (ON), wayland_server (ON)
- Shared libraries: ON (default)
- Tests: QT_BUILD_TESTS=ON; Examples: OFF

---

**编译结束**: 2026-09-14 22:05
**最终状态**: built
