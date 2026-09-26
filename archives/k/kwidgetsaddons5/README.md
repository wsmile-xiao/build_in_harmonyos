# KWidgetsAddons (KF5)

KWidgetsAddons is the KDE Frameworks widget add-on collection: a large set
of widgets and widget-related helper classes for Qt, among them
KPageWidget/KPageView for paged dialogs, KTitleWidget, KMessageWidget,
KCollapsibleGroupBox, KDatePicker/KDateTable/KDateTimeEditor,
KSelectAction/KToggleAction, KPasswordDialog/KPasswordLineEdit/
KNewPasswordWidget, KColorCombo/KColorButton, KFontRequester/KFontComboBox,
KTextEdit, KSearchClientComboBox, KMultiTabBar, KSqueezedTextLabel,
KSplitterCollapserButton, KTwoFingerSwipeRecognizer/KTwoFingerTapRecognizer,
KAcceleratorManager, KColumnResolver, and the KStatefulBrush/KColorScheme
theme helpers. This recipe tracks the KDE Frameworks 5 (Qt5) branch and
ships `libKF5WidgetsAddons.so` (SOVERSION 5); for the KF6/Qt6 branch see
`archives/k/kwidgetsaddons`.

## OHOS adaptation

- `QT_MAJOR_VERSION=5` is forced in the Conan toolchain. ECM 6.26's
  QtVersionOption defaults `BUILD_WITH_QT6=ON` (ECM >= 5.240 behavior when
  no Qt target exists yet), which would otherwise steer the KF5 branch at
  Qt6; with the variable set, `find_package(Qt5 ... Widgets)` resolves
  through the CMakeDeps-generated Qt5 config from qt5-qtbase/5.15.2.2.
- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses the KDE platform allowlist
  (OHOS/HarmonyOS is not in the upstream list).
- `BUILD_DESIGNERPLUGIN=OFF`: the Qt Designer plugin needs Qt5UiPlugin,
  which is not part of the qt5-qtbase package in this repository.
- `ecm_install_po_files_as_qm(poqm)` is patched out: Qt5LinguistTools is
  not part of the qt5-qtbase package in this repository.
- `setAccessibleName` in KPasswordDialog is guarded with
  `#ifndef QT_NO_ACCESSIBILITY`: qt5-qtbase is configured
  `-no-accessibility` (the sibling call sites carry the guard upstream).
- The qt5-qtbase package is a qmake/configure product: its native cmake
  configs are not used for target resolution. CMakeDeps regenerates a
  clean aggregated Qt5Config (`cmake_file_name=Qt5`, attica5 precedent);
  `CMAKE_AUTOMOC/AUTORCC/AUTOUIC_EXECUTABLE` point at the package bin
  tools; `qt_wrap_ui` is provisioned by including the package's
  Qt5WidgetsMacros.cmake from the generated conan_toolchain.cmake.
- `QT_CORE_LIB/QT_GUI_LIB/QT_WIDGETS_LIB/QT_TEST_LIB` are defined
  build-wide: the regenerated Qt5 configs carry no
  `INTERFACE_COMPILE_DEFINITIONS`, and without `QT_GUI_LIB` `QTEST_MAIN`
  builds tests against `QCoreApplication` without the QTest GUI helpers,
  breaking autotest compilation.
- The SONAME flags are provided explicitly
  (`CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE` +
  `CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG=-Wl,-soname,`) so the shared
  library gets an unversioned DT_SONAME (HarmonyOS is not mapped to the
  Linux CMake platform).
- The upstream autotests run headless under `QT_QPA_PLATFORM=offscreen`.
  Two tests are excluded on OHOS headless: `ktooltipwidgettest` (hangs
  under the offscreen platform plugin) and
  `kwidgetsaddons-kcolumnresizertest` (asserts native layout geometry
  that differs under offscreen) — same exclusions as the KF6 recipe.

## Dependencies

- Build: ecm (extra-cmake-modules), CMake >= 3.16, make/ninja
- Runtime/compile: qt5-qtbase (Qt5Widgets >= 5.15.2)

## References

- Homepage: https://invent.kde.org/frameworks/kwidgetsaddons
- Sources: https://download.kde.org/stable/frameworks/
