# KIconThemes

KIconThemes is a KDE Frameworks 6 library providing icon theme support on
Qt: KIconLoader for icon loading with theme fallbacks and caching, KIconTheme
for freedesktop icon theme handling, KIconEngine as a QIconEnginePlugin
backed by the theme system, plus KIconButton/KIconDialog widgets and the
KIconWidgets add-on library. Ships `libKF6IconThemes.so` and
`libKF6IconWidgets.so`.

## OHOS adaptation

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses the KDE platform allowlist
  (OHOS/HarmonyOS is not in the upstream list).
- `KICONTHEMES_USE_QTQUICK=OFF` and the patched-out `include(ECMQmlModule)`:
  Qt6Qml/Qt6Quick are not part of the qtbase package in this repository.
- `USE_DBUS=OFF`: Qt6DBus is not part of the qtbase package in this
  repository.
- `USE_BreezeIcons=OFF`: KF6BreezeIcons is not published to ohpcd; icons
  still resolve from user-installed themes.
- `BUILD_DESIGNERPLUGIN=OFF`: the Qt Designer plugin needs Qt6UiPlugin,
  which is not part of the qtbase package in this repository.
- `KF_SKIP_PO_PROCESSING=ON`: no translated catalog payload.
- ECM 6.26+ `KDEInstallDirs6` executes the qtbase `qtpaths` host tool at
  configure time; the recipe prepends `/system/lib64` to `LD_LIBRARY_PATH`
  so `qtpaths` resolves the compatible `libc++_shared.so` (the sandbox
  default contains an incompatible one under
  `/data/storage/el1/bundle/libs/arm64`).
- Upstream autotests run headless under `QT_QPA_PLATFORM=offscreen`:
  5/5 CTest targets plus the kiconloader_unittest subset (29/29 checks; one
  shared-mime-info data row is unavailable in the current OHOS baseline)
  and the kiconengine_unittest subset (8/8 checks; testMode needs
  BreezeIcons) pass on OHOS.

## Dependencies

- Build: ecm (extra-cmake-modules), CMake >= 3.29 (for 6.26.0)
- Runtime/compile: qtbase (Qt6Widgets/Qt6Gui/Qt6GuiPrivate), qtsvg,
  karchive, ki18n, kwidgetsaddons, kcolorscheme

## References

- Homepage: https://invent.kde.org/frameworks/kiconthemes
- Sources: https://download.kde.org/stable/frameworks/
