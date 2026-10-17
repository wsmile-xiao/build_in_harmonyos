# KItemViews

KItemViews is a KDE Frameworks 6 library with widget add-ons for Qt item
views: KCategorizedView/KCategoryDrawer for categorized item views,
KTreeWidgetSearchLine/KListWidgetSearchLine for incremental search over
QTreeWidget/QListWidget, KExtendableItemDelegate, and KWidgetItemDelegate
for embedding real widgets in item views. Ships `libKF6ItemViews.so`.

## OHOS adaptation

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses the KDE platform allowlist
  (OHOS/HarmonyOS is not in the upstream list).
- `BUILD_DESIGNERPLUGIN=OFF`: the Qt Designer plugin needs Qt6UiPlugin,
  which is not part of the qtbase package in this repository.
- `ecm_install_po_files_as_qm(poqm)` is patched out: Qt6LinguistTools is not
  part of the qtbase package in this repository.
- ECM 6.26+ `KDEInstallDirs6` executes the qtbase `qtpaths` host tool at
  configure time; the recipe prepends `/system/lib64` to `LD_LIBRARY_PATH`
  so `qtpaths` resolves the compatible `libc++_shared.so` (the sandbox
  default contains an incompatible one under
  `/data/storage/el1/bundle/libs/arm64`).
- The upstream autotest (`kitemviews-klistwidgetsearchlinetest`) runs
  headless under `QT_QPA_PLATFORM=offscreen` and passes 1/1 on OHOS.

## Dependencies

- Build: ecm (extra-cmake-modules), CMake >= 3.29 (for 6.26.0), ninja/make
- Runtime/compile: qtbase (Qt6Widgets)

## References

- Homepage: https://invent.kde.org/frameworks/kitemviews
- Sources: https://download.kde.org/stable/frameworks/
