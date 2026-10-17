# kwidgetsaddons5 5.116.0 notes

## Scope

New KF5 (Qt5) flavor of KWidgetsAddons for the HarmonyOS PC archive: the
large KDE widget add-on collection, built as `libKF5WidgetsAddons.so`
(SOVERSION 5). The existing `archives/k/kwidgetsaddons` entries cover the
KF6 (Qt6) branch only; this recipe ports the last KF5 release, 5.116.0,
on top of `qt5-qtbase/5.15.2.2` (which ships Qt5Widgets) and `ecm/6.26.0`.

## Adaptations

- `QT_MAJOR_VERSION=5` is forced in the toolchain: ECM 6.26's
  QtVersionOption defaults `BUILD_WITH_QT6=ON` (ECM >= 5.240 behavior when
  no Qt target exists yet), which would steer the KF5 branch at Qt6.
  `find_package(ECM 5.116.0 NO_MODULE)` is satisfied by ECM 6.26
  (AnyNewerVersion) and `KDEInstallDirs` dispatches to the
  `QT_MAJOR_VERSION=5` variants.
- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist.
- `BUILD_DESIGNERPLUGIN=OFF`: the Qt Designer plugin needs Qt5UiPlugin,
  which qt5-qtbase does not ship.
- `ecm_install_po_files_as_qm(poqm)` is commented out by patch 0001:
  qt5-qtbase does not ship Qt5LinguistTools (lconvert/lrelease). Same
  semantics as the KF6 recipe's patch, context re-anchored for 5.116.0.
- Patch 0002 guards the single unguarded `setAccessibleName` call in
  `KPasswordDialogPrivate::init` with `#ifndef QT_NO_ACCESSIBILITY`:
  qt5-qtbase is configured `-no-accessibility` (the sibling call sites in
  kcapacitybar/kcollapsiblegroupbox/kled already carry the guard upstream).
- CMakeDeps regenerates a clean aggregated `Qt5Config.cmake` via
  `set_property("qt5-qtbase", "cmake_file_name", "Qt5")` (attica5 5.116.0
  precedent); the qt5-qtbase native cmake configs are not used for target
  resolution.
- `CMAKE_AUTOMOC/AUTORCC/AUTOUIC_EXECUTABLE` point at qt5-qtbase bin tools
  (CMakeDeps exports no Qt5::moc/rcc/uic executable targets).
- `qt_wrap_ui` is provisioned by appending an include of the qt5-qtbase
  `Qt5WidgetsMacros.cmake` (with `Qt5Widgets_UIC_EXECUTABLE` set) to the
  generated `conan_toolchain.cmake`: src/ (main library) and tests/ wrap
  .ui files, and the CMakeDeps-generated Qt5 config does not define the
  upstream Qt5 macros. The append route is used instead of a handwritten
  `conan_cmakedeps_paths.cmake` because conan's toolchain skips its own
  dependency path wiring when that file exists.
- `QT_CORE_LIB/QT_GUI_LIB/QT_WIDGETS_LIB/QT_TEST_LIB` are defined
  build-wide in the same toolchain append: the CMakeDeps-regenerated Qt5
  configs carry no `INTERFACE_COMPILE_DEFINITIONS` (the native
  Qt5WidgetsConfig.cmake would set `QT_WIDGETS_LIB` etc.). Without
  `QT_GUI_LIB`, `QTEST_MAIN` instantiates `QCoreApplication` and
  `qtest.h` omits `qtest_gui.h`, so autotests using
  `QTest::keyClick/qWaitForWindowExposed` would fail to compile.
- `CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE` plus explicit
  `CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG=-Wl,-soname,`: HarmonyOS is
  not mapped to the Linux CMake platform, so the default SONAME flags are
  undefined and the ELF would lack DT_SONAME (attica5/expat-validated
  pattern, keeps the SONAME unversioned and relocatable).
- `ECM_MODULE_PATH` is set from the build-context ecm package: ecm is a
  `tool_requires`, so CMakeDeps does not wire its share/ECM tree into the
  host prefix paths automatically.
- Build/test env: `/system/lib64` and the OHOS SDK llvm lib dir are
  prepended to `LD_LIBRARY_PATH` so host tools (moc/uic/rcc) and the lld
  link steps resolve the compatible `libc++_shared.so` / `libxml2.so.16`
  (kconfig 6.26 / kwidgetsaddons 6.26 / E132 precedents).
- 5.116.0 has no `BUILD_PYTHON_BINDINGS` option (KF6 only), so unlike the
  6.x recipe it is not passed.

## Upstream tests

- CTest set (BUILD_TESTING=ON): 26 entries — 25 `ecm_add_tests` autotests
  plus `kwidgetsaddons-kcolumnresizertest` (NAME_PREFIX kwidgetsaddons-).
  The `tests/` directory holds manual GUI apps registered only via
  `ecm_mark_as_test` (built, no ctest entries).
- Exclusions on the OHOS headless runner (kwidgetsaddons 6.x precedent,
  same names in 5.116.0): `ktooltipwidgettest` (hangs under the offscreen
  platform plugin) and `kwidgetsaddons-kcolumnresizertest` (asserts native
  layout geometry that differs under offscreen).
- Execution: `ctest --output-on-failure --no-tests=error --timeout 60`
  under `QT_QPA_PLATFORM=offscreen` with XDG dirs redirected into the
  build folder.

## Verification

Local `conan create` (worktree recipe, profiles
`ci/conan/profiles/ohos-aarch64` for host and build):

- First run failed compiling autotests (`QTest::keyClick` et al. missing):
  root cause was the absent `QT_*_LIB` interface defines (see above); fixed
  by the toolchain `add_compile_definitions` append, no source patches.
- Second run: PASSED.
  - Upstream CTest: 24/24 executed tests passed (26 entries; excluded
    `ktooltipwidgettest`, `kwidgetsaddons-kcolumnresizertest`).
  - Conan test_package: 1/1 passed (`PASS: KPageWidgetModel addPage/rowCount
    OK (rows=1)`).
  - Full package reference:
    `kwidgetsaddons5/5.116.0#41481591e522c49f12a5fd9e0023871e:2affd80749999a8530e9597c2bce75e830820160#efff4798c069dbb335aaca155fef2bdf`.
  - Built ELF carries an unversioned DT_SONAME (`libKF5WidgetsAddons.so`)
    and NEEDED entries for libQt5Widgets/Gui/Core.so.5, EGL, GLESv2 and
    libc++_shared.so.
  - Log: `~/tmp/oh-device-porting-v2/kwidgetsaddons5-5.116.0/local-create-2.log`.

Upstream source SHA256 verified against download.kde.org:
`a8e1e054f16760e90d4c830b96d62ed066404f71c01f33e99f472795f9119565`.
Both patches dry-run verified with GNU patch against the unpacked 5.116.0
tarball before the build.
