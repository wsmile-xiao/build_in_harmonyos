# qtbase-gui 6.11.1 HarmonyOS PC notes

## Scope

This package is a dedicated Qt foundation for modules that need graphical Qt
APIs. It intentionally uses the Conan name `qtbase-gui` so it does not collide
with the separate Core-only `qtbase/6.11.1` prerequisite.

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
Gui and Widgets libraries required by Qt Charts.

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

The consumer test creates `QApplication` with Qt's offscreen QPA plugin, shows
a `QWidget`, processes its events, and performs real `QImage`/`QPainter`
raster drawing without requiring a display server. It also validates
`QColor`, `QHostAddress`, and `QSizePolicy`, proving that Core, Network, Gui,
Widgets, the platform-plugin loader, and the raster paint path are usable.
Native HarmonyOS window-system integration remains outside this deliberately
headless foundation package; applications that open desktop windows require a
separate native QPA backend.
