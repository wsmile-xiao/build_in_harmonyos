# Qt5 Gamepad

Qt Gamepad module for Qt5 5.15.2, providing `QtGamepad` (gamepad input
support for Qt applications).

## Build Notes
- Requires: qt5-qtbase/5.15.2.2
- Platform: HarmonyOS (aarch64)
- Build system: qmake
- No source modifications required for HarmonyOS (`patches_applied` is empty)
- Backends: evdev plugin built (qtbase evdev feature enabled); sdl2
  feature off (no pkg-config sdl2 in the dependency set); QML import
  skipped (qtbase has no qml/quick modules)
- `make install` uses `STRIP=true`: qmake's `strip --strip-unneeded`
  breaks the dynamic symbol table and makes `dlopen` fail on HarmonyOS
- Packaged `.prl`/`.la`/`.pc` files are rewritten to remove stale
  build-dir paths
- Packaged ELF shared objects are signed with `binary-sign-tool -selfSign 1`
