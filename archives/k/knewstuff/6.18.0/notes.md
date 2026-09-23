# knewstuff 6.18.0 notes

## Scope

This package provides `KF6::NewStuffCore` and `KF6::NewStuffWidgets`, required
by `grantleetheme`.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` enables the KDE Frameworks build on OHOS.
- `BUILD_DESIGNERPLUGIN=OFF` avoids Qt Designer plugin generation.
- `KF_SKIP_PO_PROCESSING=ON` skips translation catalog generation.
- `CMAKE_DISABLE_FIND_PACKAGE_KF6Kirigami2=ON` keeps optional Kirigami runtime
  discovery out of the baseline.
- `CMAKE_DISABLE_FIND_PACKAGE_KF6Syndication=ON` keeps optional OPDS feed
  support out of the baseline.
- The private QML i18n integration is guarded because the current `ki18n`
  package does not export the optional `KF6::I18nQml` target or the
  `KLocalizedQmlContext` header used by the widgets and dialog helper.
- Runtime verification prepares `DT_NEEDED` compatibility links for KF
  dependencies that were published without SONAME and therefore can reference
  stale Conan cache paths in their dynamic sections.
- Upstream install-command tests use `QTemporaryFile` via `QDir::tempPath()`;
  the recipe sets `TMPDIR`, `TEMP`, and `TMP` to an isolated writable directory
  because the OHOS target profile does not provide a writable default temporary
  directory.
- `BUILD_TESTING=ON` keeps upstream CTest coverage enabled.

## Verification

OHOS `conan create` passed:

- Upstream CTest: 4/4 passed (`knewstuff-knewstuffentrytest`,
  `knewstuff-knewstuffauthortest`, `knewstuff-knewstuffenginetest`,
  `knewstuff-installationtest`).
- `test_package`: 1/1 passed, including direct runtime smoke for
  `KF6::NewStuffCore`/`KF6::NewStuffWidgets`.
- Full reference:
  `knewstuff/6.18.0#7e9b52f4ef3bd9fcb834f39f03eccf02:a031c0166f7e4e0d24308d3ff95137f61d3e14a1#ce6cc3124001aa6cf9c97b1da2cba705`.

Not executed:

- `atticaprovidertest` is guarded by upstream with `LINUX`, so CMake does not
  build or register it for OHOS.
- `appstreamcli` validation is optional and is not registered because the tool
  is not available in the OHOS packaging profile.
- Qt API documentation targets are not generated because the required Qt tools
  packages are not part of the OHOS baseline.
- Kirigami and Syndication integration are optional KNewStuff features and are
  disabled here because this package is built for the Akonadi contact theme
  dependency chain, which consumes the core/widgets libraries.
