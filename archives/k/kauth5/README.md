# KAuth (KF5)

KAuth is the KDE Frameworks authorization framework. It lets applications
execute privileged actions through a backend/helper architecture: the
application describes an `Action`, `Backend`/`HelperProxy` decide whether the
caller is authorized, and the privileged work runs in a separate helper
process. This archive tracks the KDE Frameworks 5 (Qt5) branch and ships
`libKF5AuthCore.so` (SOVERSION 5) plus `libKF5AuthWidgets.so`; for the KF6/Qt6
branch see `archives/k/kauth`.

## OHOS adaptation

- `KAUTH_BACKEND_NAME=FAKE` and `KAUTH_HELPER_BACKEND_NAME=FAKE`. KAuth's
  native backend is PolkitQt-1, which is not published to the ohpcd remote
  (`conan download polkit-qt-1/* -r=ohpcd --only-recipe` does not resolve) and
  would additionally need a running polkit daemon. Upstream's own
  `src/ConfigureChecks.cmake` already falls back to `FAKE` when no backend is
  found, so this pins the same decision explicitly instead of relying on
  system probing. Consequence: `kauth-policy-gen` and the two plugin MODULE
  targets are not built, and the `KAuthPolicyGenTest` /
  `KAuthPolicyGenTestCompare` CTest entries are not registered (they sit in
  the same `if(NOT KAUTH_BACKEND_NAME STREQUAL "FAKE")` guard).
  `KF5::AuthCore`, `KF5::AuthWidgets`, their headers and the
  `KF5AuthConfig.cmake`/`KF5AuthTargets.cmake` files are still produced.
- `QT_MAJOR_VERSION=5`: ECM 6.20 is >= 5.240, so `QtVersionOption.cmake`
  defaults `BUILD_WITH_QT6=ON` while no Qt target exists yet; without the pin
  the project's `find_package(Qt${QT_MAJOR_VERSION} ...)` would look for Qt6.
  (`kcoreaddons5` / `kwidgetsaddons5` precedent.)
- `KF_IGNORE_PLATFORM_CHECK=TRUE`: OHOS/HarmonyOS is not in KDE's supported
  platform list (`metainfo.yaml`).
- `qt5-qtbase/5.15.2.2` is required rather than `5.15.2`: it is the first
  qt5-qtbase in this repository that ships the `Qt5Widgets` and `Qt5DBus`
  components, needed for `find_package(Qt5 ... Widgets)` and
  `find_package(Qt5DBus CONFIG REQUIRED)`. `kcoreaddons5/5.116.0` references
  `qt5-qtbase/5.15.2`, so the version family is unified with
  `override=True` (same approach as the KF6 `kauth/6.26.0` recipe). The
  override rewrites only the reference: kcoreaddons5's published binary
  already records `qt5-qtbase/5.15.Z` as its dependency and stays a
  cache/registry hit.
- The qt5-qtbase package is a qmake/configure product that ships a complete
  native CMake tree (`lib/cmake/Qt5*`, `bin/moc|rcc|uic`,
  `Qt5*Macros.cmake`, `include/QtDBus`). KAuth's Qt5 target lookup resolves
  against that native config directly, so — unlike `kwidgetsaddons5` — no
  CMakeDeps-regenerated `Qt5Config` is used; the package prefix and the ECM
  `cmake`/`share/ECM` directories are prepended to `CMAKE_PREFIX_PATH` and
  `CMAKE_MODULE_PATH` instead.
- `ecm_install_po_files_as_qm(poqm)` is patched out: qt5-qtbase in this
  repository does not ship Qt5LinguistTools (lconvert/lrelease). Same patch as
  `kcoreaddons5` / `kwidgetsaddons5` / `kconfig5`.
- HarmonyOS is not mapped to the Linux CMake platform, so the SONAME flags are
  provided explicitly (`CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG`) and the
  generated libraries get a `DT_SONAME` (CI L5 gate); `kwidgetsaddons5` /
  `attica5` validated pattern.
- The upstream autotests are built (`BUILD_TESTING=ON`) and run headless with
  `QT_QPA_PLATFORM=offscreen`. `KAuthSetupActionTest` is self-contained.
  `KAuthHelperTest` drives `DBusHelperProxy` over the *session* bus, so the
  recipe starts a private `dbus-daemon` (preferring the one shipped by the
  `dbus` package pulled in by qt5-qtbase) and tears it down afterwards; when
  no daemon can be started the test is excluded and reported as excluded,
  never counted as passing.

## Dependencies

- Build: ecm (extra-cmake-modules), CMake >= 3.16, Ninja
- Runtime/compile: qt5-qtbase (Qt5Core/Qt5Gui/Qt5Widgets/Qt5DBus/Qt5Test),
  kcoreaddons5 (KF5CoreAddons)

## References

- Homepage: https://invent.kde.org/frameworks/kauth
- Sources: https://download.kde.org/stable/frameworks/
