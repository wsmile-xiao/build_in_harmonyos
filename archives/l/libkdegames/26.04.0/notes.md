# libkdegames 26.04.0 notes

## Scope

This package provides `libKDEGames6.so` and `libKDEGames6Private.so` (cmake
package `KDEGames6`), the shared library used by KDE games such as
kfourinline. Task #13445 (KDE Games dependency chain).

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` enables the KDE build on OHOS.
- `KF_SKIP_PO_PROCESSING=ON` skips translation catalog generation (the
  `ki18n_install(po)` step is not needed for the library).
- KF6 closure at 6.18.0 (kdnssd 6.29.0), matching the upstream 26.04.0
  `.kde-ci.yml` component set: Archive, ColorScheme, Completion, Config,
  ConfigWidgets, DNSSD, GuiAddons, IconThemes, I18n, NewStuff, XmlGui.
- `karchive/6.18.0` pinned with `override=True`: the newest
  `kiconthemes/6.18.0` recipe revision requires `karchive/6.19.0` while
  `knewstuff/6.18.0` (and `knewstuff/6.26.0`) require `karchive/6.18.0`;
  without the override conan reports a version conflict inside the graph.
- Qt6 Qml/Quick come from `qtdeclarative/6.11.1` and Qt6 Svg from
  `qtsvg/6.11.1`, passed via `QT_ADDITIONAL_PACKAGES_PREFIX_PATH`.
- OpenAL and SndFile are located through their upstream CMake config files
  (`OpenALConfig.cmake`, `SndFileConfig.cmake`) from the conan packages; the
  configure-time `try_compile` libsndfile capability check passes.
- `svgcleaner`/`7Zip` stay optional and absent; carddecks SVGZ generation
  uses the `gzip -9 -n -c` fallback. `BUILD_SVG_CHECKS=OFF` (default) keeps
  ImageMagick out of the build.
- `BUILD_TESTING=ON` keeps the upstream CTest suite enabled.

## Verification

OHOS `conan create` passed:

- Upstream CTest: 2/2 passed (`libkdegamesprivate-kgamesvgdocumenttest`,
  `libkdegamesprivate-kgamepropertytest`).
- `test_package`: 1/1 passed (KGameClock/KGameTheme/KGamePopupItem consumer
  compile + link + runtime smoke with the offscreen platform).
- Full reference:
  `libkdegames/26.04.0#6c2947fbfc8c12b5d33db598b6a31b20:53177846b8b3702149a9a58a031101b0207dd639#43e26ccaa165d46607546185e1f7afd0`.

Upstream test registration notes:

- `tests/kgamepopupitemtest` is compiled but never registered via
  `add_test` by upstream CMake (it is a manual GUI executable), so it is not
  part of the ctest count.
- `src/private/tests` registers 2 tests via `ecm_add_tests` with the
  `libkdegamesprivate-` name prefix.
- The `check-libsndfile-capabilities` `try_compile` runs at configure time
  and passed.
- Upstream ctest count for this version: 2 registered tests, 2 executed,
  2 passed (100%).

## Test package behavior notes

- The consumer smoke exercises KGameClock (restart/pause/resume/setTime/
  timeString), KGameTheme (identifier/metadata roundtrip,
  readFromDesktopFile rejection of a nonexistent path) and KGamePopupItem
  (scene registration, timeout/opacity, hidesOnMouseClick roundtrip,
  forceHide). `showMessage()` is intentionally not called: it starts a
  QVariantAnimation that requires a running event loop with a paint engine
  and segfaults in a headless offscreen process without `app.exec()`.
- ctest replaces the test process environment when the `ENVIRONMENT`
  property is set, so the LD_LIBRARY_PATH of every dependency lib dir (plus
  the mirrored `bin/` symlink dir) is baked into the property through the
  `LKG_TEST_LIB_DIRS` cache variable written by the conanfile generate().
