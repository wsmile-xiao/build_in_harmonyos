# KNotifications

KNotifications is a KDE Frameworks 6 library for desktop notifications:
KNotification is the main class for creating notifications (events,
actions, icons, flags), plus KNotificationPermission,
KNotificationReplyAction and KNotifyConfig. Ships
`libKF6Notifications.so`.

## OHOS adaptation

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses the KDE platform allowlist
  (OHOS/HarmonyOS is not in the upstream list).
- `BUILD_DESIGNERPLUGIN=OFF`: the Qt Designer plugin needs Qt6UiPlugin,
  which is not part of the qtbase package in this repository.
- `USE_DBUS=OFF` plus patch disabling the DBus+Canberra block: Qt6DBus is
  not published as a component in the qtbase package and libcanberra is not
  yet published to the ohpcd registry (PR #8498 in flight); the audio
  notification backend (`notifybyaudio.cpp`) and DBus popup/portal backends
  are therefore not compiled in this build.
- `BUILD_PYTHON_BINDINGS` is patched back to quiet probing (6.26 upstream
  changed it from cmake_dependent_option to a plain option with REQUIRED
  find_package calls); Shiboken6/PySide6 are not published so bindings are
  auto-disabled.
- `ecm_install_po_files_as_qm(poqm)` is patched out: Qt6LinguistTools is not
  part of the qtbase package in this repository.
- ECM 6.26+ `KDEInstallDirs6` executes the qtbase `qtpaths` host tool at
  configure time; the recipe prepends `/system/lib64` to `LD_LIBRARY_PATH`
  so `qtpaths` resolves the compatible `libc++_shared.so`.
- Upstream CTest suite: the autotest `KNotificationTest` is commented out
  upstream and requires a DBus session bus; the `tests/` executables are
  HAVE_DBUS-guarded. With USE_DBUS=OFF the upstream add_test count is 0
  (headless CI has no DBus session bus — platform limitation). The consumer
  smoke test in test_package exercises the KNotification API surface.

## Dependencies

- Build: ecm (extra-cmake-modules), CMake >= 3.29 (for 6.26.0)
- Runtime/compile: qtbase (Qt6Gui), kconfig

## References

- Homepage: https://invent.kde.org/frameworks/knotifications
- Sources: https://download.kde.org/stable/frameworks/
