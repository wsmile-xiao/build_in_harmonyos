# kiconthemes 6.18.0 notes

## Scope

This package is part of the Akonadi KF 6.18 baseline. It is based on the
existing remote 6.14.0 recipe and adds a mainline-ready 6.18.0 package
directory without modifying the 6.14.0 branch.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `KICONTHEMES_USE_QTQUICK=OFF` avoids Qt6Qml/Qt6Quick.
- `USE_DBUS=OFF` avoids Qt6DBus until the shared Qt DBus baseline lands.
- `USE_BreezeIcons=OFF` avoids the unpublished KF6BreezeIcons package.
- `BUILD_DESIGNERPLUGIN=OFF` avoids Qt6UiPlugin.
- `BUILD_TESTING=ON` enables the upstream CTest/autotests suite during the
  OHOS Conan package build.
- `KF_SKIP_PO_PROCESSING=ON` avoids translation catalog generation.
- `include(ECMQmlModule)` is patched out for the Qt6Qml-free baseline, and the
  optional QtQuick autotest is guarded behind `KICONTHEMES_USE_QTQUICK`.

## Verification

The recipe also supplies consumer-side `OPENSSL_*` cache variables and a minimal `PkgConfig::LibZstd` imported target because the reused `karchive/6.19.0` package exports those dependencies through its installed CMake config.


Initial local checks:

- Upstream source SHA256 verified:
  `b971460949fafc98e7ae293f35635c2fd6101a6fc46b2f4fce64bb21440ece04`.
- The CMake patch was checked against the unpacked 6.18.0 source.

OHOS `conan create` verification passed on 2026-08-19.

- Runner log: `/storage/Users/currentUser/ohos-users/codex-a/kf618-kitemviews-upstream-low-20260819/logs/kiconthemes-r5.log`.
- Full package reference: `kiconthemes/6.18.0#238238cf0ff8e2fe25ca51b5fa345b64:68da9b6f71843f6180aff75c81513a96ba64b986#683912ead7d4ad701240b1c2f0291c07`.
- Runner results: L0 pass, L1 pass, L5 pass; L2 skip: kiconfinder6 version/help failed; L4 pass.
- Upstream CTest passed 5/5: `kiconloader_resourcethemetest`,
  `kicontheme_unittest`, `kiconengine_scaled_unittest`,
  `kicondialog_unittest`, and `kpixmapsequenceloadertest`.
- Upstream `kiconloader_unittest` passed the OHOS-supported subset: 29/29
  QtTest checks, excluding one data row that depends on shared-mime-info data
  unavailable in the current OHOS baseline.
- Upstream `kiconengine_unittest` passed the OHOS-supported subset: 8/8
  QtTest checks, excluding `testMode` because BreezeIcons is explicitly
  disabled for the current OHOS baseline.
- Upstream `kquickiconprovidertest` was not registered or executed because
  Qt6Qml/Qt6Quick are not published in the current OHOS baseline and
  `KICONTHEMES_USE_QTQUICK=OFF` disables that optional integration.
- Conan `test_package` passed 1/1 with a `KIconLoader::global()` consumer
  compile/link/runtime smoke.
