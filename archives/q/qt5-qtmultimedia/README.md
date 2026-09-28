# Qt5 Multimedia

Qt Multimedia module for Qt5 5.15.2, providing `QtMultimedia` / `QtMultimediaWidgets`
(media playback, audio devices, camera/radio control interfaces).

## Build Notes
- Requires: qt5-qtbase
- Platform: HarmonyOS (aarch64)
- Build system: qmake
- No source modifications required for HarmonyOS (`patches_applied` is empty)
- `make install` uses `STRIP=true`: qmake's `strip --strip-unneeded` breaks the
  dynamic symbol table and makes `dlopen` fail on HarmonyOS
- Packaged `.prl`/`.la`/`.pc` files are rewritten to remove stale build-dir paths
