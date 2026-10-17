# KJobWidgets (KF5)

KJobWidgets is the KDE Frameworks 5 bridge between `KJob` (from KCoreAddons)
and the widgets that display job progress. It ships `libKF5JobWidgets.so`
(SOVERSION 5) and provides:

- `KWidgetJobTracker` — progress dialog for a running job
- `KStatusBarJobTracker` — progress widget embedded in a `QStatusBar`
- `KUiServerJobTracker` / `KUiServerV2JobTracker` — D-Bus based job views
  (compiled in only when the Qt5 DBus component is available)
- `KDialogJobUiDelegate` — error/skip dialogs for a job
- `KJobWidgets` / `KJobWindows` — associate a job with a `QWidget` / `QWindow`

This recipe tracks the KDE Frameworks 5 (Qt5) branch; for the KF6/Qt6 branch
see `archives/k/kjobwidgets`.

## Why this package

`kjobwidgets5/5.116.0` is a direct, REQUIRED build dependency of **KParts 5**
(`find_package(KF5JobWidgets ...)` in `kparts/CMakeLists.txt`). KParts 5 itself
cannot be adapted yet because 7 of its 10 REQUIRED KF5 dependencies have no
published 5.116.0 recipe, so the dependency chain is being closed bottom-up
(R36 — dependencies must be published before downstream packages).

## OHOS adaptation

- `QT_MAJOR_VERSION=5` is forced in the Conan toolchain; `qt5-qtbase/5.15.2.2`
  (the Widgets + DBus capable build) is consumed, not the plain `5.15.2`
  `-no-widgets` stub.
- `CMAKE_SYSTEM_NAME=Linux`: the OHOS toolchain maps `os=OHOS` to
  `CMAKE_SYSTEM_NAME=HarmonyOS`, for which CMake defines neither `UNIX` nor a
  platform module and which makes the build look like a cross build. Forcing
  the Linux platform (same libc / clang driver) restores `UNIX=1`, ECM's POSIX
  flag/rpath handling and the upstream ctest registration semantics.
- `WITH_X11=OFF`: HarmonyOS PC has no X11 window system and no X11 headers, so
  `HAVE_X11` is off and the `QX11Info` branch of `KDialogJobUiDelegate` is
  compiled out; no `Qt5::X11Extras` lookup is attempted.
- `KF_SKIP_PO_PROCESSING=ON` plus `patches/0001-CMakeLists.txt.patch` disable
  `ecm_install_po_files_as_qm(poqm)`, which requires Qt5LinguistTools
  (`lconvert`/`lrelease`) — not part of the published qt5-qtbase package.
- Unversioned `DT_SONAME` (`CMAKE_PLATFORM_NO_VERSIONED_SONAME` +
  `-Wl,-soname,`) and `CMAKE_BUILD_WITH_INSTALL_RPATH=ON`: OHOS has no CMake
  platform module so the soname linker flag stays unset (E537 — consumers would
  record a path-form `DT_NEEDED`), and the install-time in-place RPATH rewrite
  must be avoided so the installed ELF keeps loading.
- `qt5-qtbase` is consumed through its own Qt5 CMake configs
  (`cmake_find_mode=none`), with `CMAKE_{AUTOMOC,AUTORCC,AUTOUIC}_EXECUTABLE`
  pointed at the package bin tools and the mkspec tree mirrored next to the
  package prefix.
- `CMAKE_BUILD_PARALLEL_LEVEL=1`: HMDFS refuses the make jobserver fifo.

## Upstream tests

Upstream registers **no** ctest cases: `autotests/CMakeLists.txt` only holds a
commented-out `ecm_add_tests()` template, and the two programs in `tests/`
(`kjobtrackerstest`, `kjobcreator`) are interactive GUI demos built with
`add_executable` + `ecm_mark_as_test()` — which attaches labels but never calls
`add_test()`. Measured: `ctest -N` reports `Total Tests: 0`. Because the suite
is genuinely empty, `ctest` is deliberately **not** embedded in `build()`
(an empty suite returning rc=0 would fake an L1 test trail). Consumer-side
coverage is provided by `test_package/test.cpp`, which drives the real
`KF5::JobWidgets` API. Details and evidence: `5.116.0/notes.md` and
`5.116.0/reports/`.

## Versions

| Version | Status | Build system | Notes |
|---------|--------|--------------|-------|
| 5.116.0 | built | cmake | KF5/Qt5 branch; dependency of kparts5 |
