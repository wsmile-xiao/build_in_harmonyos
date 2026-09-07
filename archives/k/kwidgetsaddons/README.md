# KWidgetsAddons

KWidgetsAddons is a KDE Frameworks 6 library with a large collection of
widgets and widget-related helper classes for Qt: KPageWidget/KPageView for
paged dialogs, KTitleWidget, KMessageWidget, KCollapsibleGroupBox,
KDatePicker/KDateTable/KDateTimeEditor, KSelectAction/KToggleAction,
KPasswordDialog/KPasswordLineEdit/KNewPasswordWidget, KColorCombo/
KColorButton, KFontRequester/KFontComboBox, KTextEdit, KSearchClientComboBox,
KUriLabel, KMultiTabBar/KMultiTabBarButton, KTitleWidget, KSqueezedTextLabel,
KSplitterCollapserButton, KTwoFingerSwipeRecognizer/KTwoFingerTapRecognizer,
KAcceleratorManager, KColumnResolver, plus the KStatefulBrush and
KColorScheme color/metrics theme helpers. Ships `libKF6WidgetsAddons.so`.

## OHOS adaptation

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses the KDE platform allowlist
  (OHOS/HarmonyOS is not in the upstream list).
- `BUILD_PYTHON_BINDINGS=OFF`: upstream defaults the option to ON (guarded
  off only for ANDROID/APPLE/WIN32/HAIKU or static builds) and would try to
  discover Shiboken6/PySide6, which are not published on ohpcd.
- `BUILD_DESIGNERPLUGIN=OFF`: the Qt Designer plugin needs Qt6UiPlugin,
  which is not part of the qtbase package in this repository.
- `ecm_install_po_files_as_qm(poqm)` is patched out: Qt6LinguistTools is not
  part of the qtbase package in this repository.
- ECM 6.26+ `KDEInstallDirs6` executes the qtbase `qtpaths` host tool at
  configure time; the recipe prepends `/system/lib64` to `LD_LIBRARY_PATH`
  so `qtpaths` resolves the compatible `libc++_shared.so` (the sandbox
  default contains an incompatible one under
  `/data/storage/el1/bundle/libs/arm64`).
- The upstream autotests run headless under `QT_QPA_PLATFORM=offscreen`.
  Two tests are excluded on OHOS headless: `ktooltipwidgettest` (hangs under
  the offscreen platform plugin) and `kwidgetsaddons-kcolumnresizertest`
  (asserts native layout geometry that differs under offscreen).

## Dependencies

- Build: ecm (extra-cmake-modules), CMake >= 3.29 (for 6.26.0), ninja/make
- Runtime/compile: qtbase (Qt6Widgets)

## References

- Homepage: https://invent.kde.org/frameworks/kwidgetsaddons
- Sources: https://download.kde.org/stable/frameworks/
