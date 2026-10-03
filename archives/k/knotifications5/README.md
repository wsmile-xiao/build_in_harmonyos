# knotifications5 (KNotifications KF5)

knotifications is the KDE Frameworks 5 desktop notification library:
KNotification is the main class for creating notifications (events,
actions, icons, flags), plus KPassivePopup, KStatusNotifierItem,
KNotificationJobUiDelegate, KNotificationReplyAction,
KNotificationRestrictions and KNotifyConfig. Ships
`libKF5Notifications.so`.

## OHOS adaptation (KF5 / Qt5 chain)

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses the KDE platform allowlist
  (OHOS/HarmonyOS is not in the upstream list).
- Qt5DBus is not available in the packaged OHOS Qt5 (qt/5.15.19 is built
  `-no-dbus`): the DBus+Canberra/Phonon REQUIRED blocks, the
  `if (TARGET Qt5::DBus)` source/link guards and the `HAVE_DBUS`
  assignment are disabled via patches 0001-0003, so the DBus popup/portal
  backends, the StatusNotifierItem DBus backend, KNotificationRestrictions
  and the audio notification backend are not compiled.
- `knotificationmanager.cpp` patched (0004): the Popup plugin include and
  instantiation get a `QT_DBUS_LIB` guard (upstream `#else` assumes DBus on
  non-Android/Mac/Win); the Popup action degrades to NotifyByTaskbar.
- `ecm_install_po_files_as_qm(poqm)` patched out: Qt5LinguistTools is not
  shipped by the packaged OHOS Qt5.
- `examples/` skipped: they need Qt5 Quick (qtdeclarative, unpublished).
- `CMAKE_SYSTEM_NAME=Linux` forced: the OHOS CMake platform lacks
  Platform/HarmonyOS so `UNIX` is unset and KDE `if(UNIX)` source
  selection would drop sources (kcoreaddons5 precedent).
- SONAME flags injected for the Generic CMake platform (E330).
- Installed ELFs re-signed with binary-sign-tool (OHOS loader rejects the
  lld placeholder signature; qt/5.15.19 precedent).

## Dependencies

- qt5-qtbase/5.15.2.2 (Qt5 Core/Gui/Widgets; pinned with `override=True`
  to unify the 5.15.2 declared by kcoreaddons5)
- kcoreaddons5/5.116.0, kconfig5/5.116.0, kwindowsystem5/5.116.0
- ecm/6.26.0 (build)
