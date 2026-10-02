# qqc2-breeze-style 6.7.5 notes

## Scope

KDE Plasma QML style plugin for Qt Quick Controls 2 ("org.kde.breeze"),
required by the Plasma 6.7 desktop style stack. The package ships:

- `qml/org/kde/breeze/` — QML style module (27 QQC2 control templates)
- `libBreezeImpl.so` — internal C++ helper library for the QML module
- `libplugins/kf6/kirigami/platform/org.kde.breeze.so` — Kirigami
  platform theme plugin (plasma-desktop integration)

## Why the Qt6/KF6 6.26 dependency line

Upstream `CMakeLists.txt` pins `QT_MIN_VERSION 6.10.0` and
`KF6_MIN_VERSION 6.26.0`. The task's original dependency hint mentioned the
Qt5 line (qt5-qtdeclarative/qt5-qtsvg); the 6.7.5 source requires Qt6, so
the recipe uses the published Qt6 line (qtbase/qtdeclarative/qtsvg/
qtshadertools 6.11.1) and KF6 6.26 components (kguiaddons/kconfig/
kcolorscheme/kiconthemes), with kirigami 6.26.0 providing KirigamiPlatform
(kirigami 6.18.0's KF6KirigamiPlatformConfig is rejected by FindKF6's
6.26 minimum-version check — verified in the first local conan create
failure).

## OHOS adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` — OHOS is not in KDE's platform list.
- `USE_DBUS=OFF` — the style payload does not need the DBus code path.
- `KF_SKIP_PO_PROCESSING=ON` — no translation catalogs on the OHOS build.
- `BUILD_TESTING=OFF` — the 6.7.5 release tarball ships no `autotests/`
  directory (upstream tests live in the git CI branch); QML style tests
  additionally require a display server the sandbox does not provide.
  Consumer coverage: `test_package/test_qqc2.cpp` loads the installed
  `org.kde.breeze` QML style through the QQmlEngine import path and
  verifies >= 20 of the 27 QQC2 control templates resolve.
- CMake prefix/module paths are bridged manually through
  `conan_cmakedeps_paths.cmake` because qtbase uses `cmake_find_mode=none`
  (kirigami 6.18.0 / kiconthemes 6.26.0 precedent).
- `/system/lib64` is prepended to `LD_LIBRARY_PATH` during configure and
  test runs to keep the compatible libc++ first in loader order
  (kconfig 6.26.0 precedent).

## Upstream tests

- The 6.7.5 release tarball has **no** `autotests/` directory (verified by
  listing the extracted source: only `CMakeLists.txt`, `LICENSES/`,
  `QQC2BreezeStyleConfig.cmake.in`, `README.md`, `getqmlobjects.py`,
  `kirigami-plasmadesktop-integration/`, `style/`) — upstream QML autotests
  exist only in the git repository's CI configuration and require a working
  display server (offscreen QML scene rendering).
- Platform constraint (reported as-is): no display environment in the
  OHOS build sandbox; consumer test covers style payload integrity.

## Verification

- Source SHA256 verified against the KDE download server tarball:
  `788f0698c904112cc33bf6f8fb446b2e4fd7231d38c0955cbc3baa50d375d1ee`.
- Local `conan create` with the ohos-aarch64 profile (jobs=2) **PASSED**
  on 2026-09-29: build 100%, package installed, consumer test
  `control QML files found: 27/27`, kirigami platform plugin payload
  present, QML import path registered — exit 0.
- Initial local run exposed a test-package path bug (the style installs
  under `lib/qml/org/kde/breeze`, not `qml/org/kde/breeze`, per
  KDEInstallDirs with CMAKE_INSTALL_LIBDIR=lib); the consumer test now
  accepts both layouts and canonicalizes import paths for comparison.
- CI re-validates on a clean worker.
