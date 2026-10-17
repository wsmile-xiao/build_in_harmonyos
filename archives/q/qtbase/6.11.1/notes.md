# qtbase 6.11.1 HarmonyOS PC notes

## Scope

This package is the Qt Base foundation for Qt 6 modules that need Core,
Network, Gui, Widgets and Xml APIs on HarmonyOS PC. It intentionally uses the
Conan name `qtbase` so downstream Qt modules can resolve `qtbase/6.11.1`
directly.

The source archive keeps the upstream Qt sha256 and lists multiple Qt mirrors
before the official `download.qt.io` URL. This avoids CI worker timeouts on the
large `qtbase-everywhere-src-6.11.1.tar.xz` download while preserving identical
source verification.

Built modules:

- Qt Core
- Qt Network
- Qt Gui
- Qt Widgets, including QGraphicsView support
- Qt Xml

## Reduced platform surface

The package uses Qt's raster functionality and bundled third-party libraries.
External desktop or graphics stacks are disabled: XCB/Xlib, OpenGL/EGL,
Vulkan, DBus, CUPS/PrintSupport, GTK, fontconfig, libinput, evdev and tslib.
This keeps the package independent of a window server while retaining the real
Gui and Widgets libraries required by downstream Qt 6 modules.

## HarmonyOS adaptations

The first five portability patches are derived from the already CI-validated
qtbase PR #2889. The sixth was identified by building this graphical variant
on the shared HarmonyOS device:

1. Recognize HarmonyOS as a Linux-compatible UNIX platform.
2. Add the `harmonyos-clang` mkspec.
3. Disable unavailable pthread cancellation paths through a capability macro.
4. Reuse CMake's Linux shared-library rules for SONAME and RPATH behavior.
5. Skip Qt's pre-project Android autodetection for the HarmonyOS mkspec.
6. Define `QT_NO_ARM_AES_INTRINSICS` for OHOS and use it to disable Qt's ARM
   AES qHash path. The compiler advertises the crypto target feature, but the
   platform NEON headers do not provide `vaeseq_u8` and `vaesmcq_u8`; Qt's
   portable fallback remains correct.

Installed shared libraries are re-signed after CMake installation because
RPATH changes invalidate the original HarmonyOS code signature.

## Test strategy

The recipe enables Qt Test without adding the full upstream matrix to the
default build. It explicitly builds and executes seven upstream test
executables: QColor, QHostAddress, QSizePolicy, QWidget, QImage, QPainter and
QDom. CTest runs them with the offscreen QPA backend and reports an explicit
7-test pass rate (all 7 pass).

An additional 19 extended upstream tests (Core/Network/Xml) were built and run
separately (not part of the default package build): tst_qstring, tst_qlist,
tst_qhash, tst_qfile, tst_qdir, tst_qurl, tst_qtimer, tst_qbytearray,
tst_qxmlstream, tst_qstringlist, tst_qdatetime, tst_qcryptographichash,
tst_qmap, tst_qset, tst_qregularexpression, tst_qvariant, tst_json,
tst_qprocess, tst_qsettings. 15 of 19 pass; the 4 partial/failing groups are
platform-specific: qfile/qdir (HMDFS does not honor chmod/mkdir mode bits,
E046), qsettings (case-insensitive HMDFS filesystem) and qdatetime
(springForward: QtTest data-row mismatch on OHOS tzdata). Overall 56200 of
which 55142 passed (98.1%). Full per-test numbers are in manifest.yaml
`test_results`.

The consumer test creates `QApplication` with Qt's offscreen QPA plugin, shows
a `QWidget`, processes its events, and performs real `QImage`/`QPainter`
raster drawing without requiring a display server. It also validates
`QColor`, `QHostAddress`, and `QSizePolicy`, proving that Core, Network, Gui,
Widgets, the platform-plugin loader, and the raster paint path are usable.
Native HarmonyOS window-system integration remains outside this deliberately
headless foundation package; applications that open desktop windows require a
separate native QPA backend.

## Patch maintenance note

The recipe keeps the original 6 committed patches (including the
`harmonyos-clang` mkspec). Do NOT re-run `refresh-patch --auto` on this archive:
it regenerates 5 per-file patches that lose the mkspec addition and the
original patch names referenced by conandata.yml. The patches are restored
from git HEAD; conandata.yml and conanfile.py stay byte-identical to the
published registry recipe (L0j).

## Local build-worker GLib limitation (do NOT change the recipe)

The shared build worker's `/storage/Users/currentUser/usr/local` contains a
static `libglib-2.0.a` whose `g_libintl_*` gettext wrapper symbols have no
shared provider on OHOS, so linking Qt's GLib event dispatcher fails locally.
This is a build-worker environment difference only: the published
qtbase/6.11.1 recipe (revision 714d84d0, 2026-08-04) was built successfully by
CI. To verify locally, temporarily isolate the worker GLib (e.g. rename
`libglib-2.0.a`, `glib-2.0.pc`, and the `include/glib-2.0` tree out of
`/storage/Users/currentUser/usr/local`) during `conan create`, then restore.
The recipe itself must NOT add `FEATURE_glib=OFF` — that would break the L0j
version gate.
---

**编译结束**: 2026-08-11 17:47
**最终状态**: built
