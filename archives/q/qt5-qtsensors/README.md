# Qt5 QtSensors

Qt Sensors module for Qt5 5.15.2, providing the `QtSensors` C++ library
(sensor framework: QAccelerometer/QCompass/QGyroscope/... reading classes,
QSensorManager backend registry), sensor backend plugins, sensor gesture
plugins and the `QtSensors` QML import module.

## Build Notes
- Requires: qt5-qtbase, qt5-qtdeclarative (QML imports)
- Platform: HarmonyOS (aarch64)
- Build system: qmake
- No source modifications required for HarmonyOS (`patches_applied` is empty);
  hardware backend selection uses the upstream official qmake variable
  `SENSORS_PLUGINS=generic` (the default linux set would build the linuxsys
  backend which reads `/dev/input` — absent on OHOS PC — and the
  iio-sensor-proxy backend which requires a system D-Bus daemon and segfaults
  on load when absent)
- `make install` uses `STRIP=true`: qmake's `strip --strip-unneeded` breaks the
  dynamic symbol table and makes `dlopen` fail on HarmonyOS
- Packaged `.prl`/`.la`/`.pc` files are rewritten to remove stale build-dir paths
- All packaged `.so` files are signed with binary-sign-tool
