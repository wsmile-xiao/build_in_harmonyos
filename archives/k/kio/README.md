# KIO

KIO is the KDE Frameworks 6 input/output and networking layer. It provides
libKF6KIOCore (KIO jobs, KFileItem, the global KIO API, URL utilities,
protocol registry), the kioworker host process and the per-protocol worker
plug-ins (file/remote/trash in the OHOS baseline) that applications use for
asynchronous file operations, transparent remote access and MIME handling.

Two versions are archived side by side: 6.26.0 (KIOCore-only baseline) and
6.14.0 (full-stack build); each has its own OHOS adaptation section below.

## OHOS adaptation (6.26.0 baseline)

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

## OHOS adaptation (6.14.0)

6.14.0 is built as a full stack and shares the generic switches above
(platform allowlist bypass, DBus/X11/Wayland/designer-plugin off, libxml2
`LD_LIBRARY_PATH` injection). Version-specific points:

- Full-stack build: KF6KIOCore, KF6KIOGui, KF6KIOWidgets, KF6KIOFileWidgets
  and the `file://` KIO worker. The KF6 6.14 GUI/widget dependency set is
  published on ohpcd, so no `KIOCORE_ONLY` trimming is needed; the
  SSL-dependent surface is instead trimmed by patches (KSSL classes in
  KIOCore/KIOWidgets, ftp/http workers, `showSslDetails` degraded to a
  no-op) because qtbase Qt6Network is built without SSL.
- 17 patches total: platform guards (OHOS sets `CMAKE_SYSTEM_NAME=OHOS`, so
  CMake `UNIX` is false; the KAuth find_package gate and Unix-only guards
  are rewritten), KAuth camelCase includes rewritten to the lowercase
  case-sensitive headers actually installed, C++20 `std::ranges` rewritten
  to C++17 iterator pairs (ohos-aarch64 profile pins cppstd=17).
- Patch 0015 fixes `DT_SONAME` at link time (`-Wl,-soname` for the four KIO
  libraries); post-build ELF rewriting is impossible on OHOS (in-place
  rewrite invalidates `.codesign` signatures and modified ELF files are
  denied exec, so repairs must happen at link time).
- Patch 0016: KProcessRunner self-deletes on `QProcess::FailedToStart`
  (exec failures never emit `finished()`, which leaked the instance and its
  KProcess).
- Patch 0017: KShortUriFilter no longer appends a second `://` when the
  default scheme already carries one (prevents malformed `https:////host`
  URIs when the ksycoca protocol registry lacks the default scheme entry).
- `ECM_MODULE_PATH` is injected manually and `conan_cmakedeps_paths.cmake`
  is written by `generate()` (CMakeDeps-generated ECMConfig.cmake does not
  propagate the module path; qtbase uses `cmake_find_mode=none`).
- Status: authoritative device CI green; the binary is not yet published to
  the artifact repo and is released after the recipe merge.
