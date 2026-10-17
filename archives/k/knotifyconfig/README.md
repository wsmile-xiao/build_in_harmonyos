# KNotifyConfig

KNotifyConfig is the KDE Frameworks 6 notification configuration widget:
`KNotifyConfigWidget` lets an application show a dialog for its own
notification events (which action fires — sound, popup — and which sound
file). Ships `libKF6NotifyConfig.so.6`.

## OHOS adaptation

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses the KDE platform allowlist
  (OHOS/HarmonyOS is not in the upstream list).
- `USE_DBUS=OFF`: Qt6DBus is not published to ohpcd. The `HAVE_DBUS` block
  only guards the post-save "ask KNotification objects to reload" broadcast.
- The notification sound field used `KUrlRequester`, which lives in
  `KF6::KIOWidgets`. ohpcd builds kio in KIOCORE_ONLY mode
  (`solid` / `kbookmarks` / `kjobwidgets` / `kiconthemes` 6.26 are
  unpublished), so three patches replace it: the target links
  `KF6::KIOCore`, the `.ui` sound field becomes a plain `QLineEdit` (and the
  now-dangling `<customwidgets>` block is removed so uic stops including
  `kurlrequester.h`), and the KUrlRequester-only `setStartDir` /
  `setMimeTypeFilters` / `setUrl` calls are dropped in favour of the
  `QLineEdit` text accessors. `textChanged(QString)` has the same signature
  on both classes, so the existing `connect()` needs no change.
- `ki18n_install(po)` is skipped on OHOS: the macro shells out to
  Qt6LinguistTools / gettext, which are not published to ohpcd. Runtime i18n
  still resolves through `KF6::I18n`.
- `BUILD_TESTING=OFF`: `tests/` requires KF6ConfigWidgets, KF6Notifications,
  KF6WidgetsAddons and KF6XmlGui at 6.26 plus Qt6Test; ohpcd only carries
  6.14.0/6.18.0 of those frameworks. The upstream `knotifytest` target is a
  GUI demo without assertions anyway — the real verification lives in
  `test_package`.
- Native OHOS builds leave CMake in the Generic platform module (no
  `CMAKE_SYSTEM_NAME` when `os_build == os_host == OHOS`), which has no
  shared-library SONAME rule. The recipe sets
  `CMAKE_SHARED_LIBRARY_SONAME_{CXX,C}_FLAG` manually so
  `libKF6NotifyConfig.so.6` keeps its `DT_SONAME`.
- ECM 6.26+ `KDEInstallDirs6` executes the qtbase `qtpaths` host tool at
  configure time; the recipe prepends `/system/lib64` to `LD_LIBRARY_PATH`
  so `qtpaths` resolves the compatible `libc++_shared.so`.
- Installed ELF files are re-signed: CMake rewrites the RUNPATH of an
  installed shared library, which invalidates the OHOS build-time
  `.codesign` section and makes the loader refuse the library
  ("Permission denied"). See kiconthemes 6.26.0.

## Dependencies

- Build: ecm (extra-cmake-modules), CMake >= 3.29
- Compile: qtbase (Qt6Widgets), qtmultimedia (sound preview), kcompletion,
  kconfig, ki18n, kio (KF6::KIOCore)

## References

- Homepage: https://invent.kde.org/frameworks/knotifyconfig
- Sources: https://download.kde.org/stable/frameworks/6.26/
