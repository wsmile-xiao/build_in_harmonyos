# KIO

KIO is the KDE Frameworks 6 input/output and networking layer. It provides
libKF6KIOCore (KIO jobs, KFileItem, the global KIO API, URL utilities,
protocol registry), the kioworker host process and the per-protocol worker
plug-ins (file/remote/trash in the OHOS baseline) that applications use for
asynchronous file operations, transparent remote access and MIME handling.

## OHOS adaptation

- `KIOCORE_ONLY=ON` baseline: only KF6KIOCore, the kioworker executable and
  the file/remote/trash workers are built. KIOGui/KIOWidgets/KIOFileWidgets
  and the ftp/http workers are left out because several of their KF6 6.26
  dependencies (solid, kbookmarks, kcolorscheme, kjobwidgets, kiconthemes)
  are not published on ohpcd and Qt6Network is built without SSL.
- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses the KDE platform allowlist
  (OHOS/HarmonyOS is not in the upstream list).
- `USE_DBUS=OFF` (no kdbusaddons 6.26 package / no session bus),
  `WITH_X11=OFF`, `WITH_WAYLAND=OFF`, `BUILD_DESIGNERPLUGIN=OFF`.
- The OHOS SDK lld needs `libxml2.so.16` at link time: libxml2/2.15.3 is
  declared as a requirement and its lib dir is injected into
  `LD_LIBRARY_PATH` (E132, kservice 6.26 precedent); `/system/lib64` is
  prepended so the qtbase `qtpaths` host tool resolves the compatible
  `libc++_shared.so` (kconfig 6.26 precedent).
- `CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG` is set manually because CMake has
  no `Platform/HarmonyOS` module (kfilemetadata/baloo precedent).
