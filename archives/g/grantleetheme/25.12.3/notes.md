# grantleetheme 25.12.3 notes

## Scope

This package provides `KPim6::GrantleeTheme`, required by
`akonadi-contacts`.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` enables the KDE Frameworks build on OHOS.
- `KF_SKIP_PO_PROCESSING=ON` skips translation catalog generation.
- `BUILD_QCH=OFF` skips Qt Assistant documentation.
- `BUILD_TESTING=ON` keeps upstream CTest coverage enabled.
- `karchive/6.18.0` is used as a graph override because `knewstuff/6.18.0`
  was verified against that version, while `kxmlgui/6.18.0` published binaries
  were built against `karchive/6.19.0`.
- `kiconthemes` is overridden to `6.18.0.1`: the repackaged recipe is built
  against the `karchive/6.18.0` closure, so its published binary
  (5937e6fd91b6589196a15790f369a1328a4907fb) is reused instead of rebuilding
  `kiconthemes/6.18.0` from source. This keeps the whole dependency graph on
  published ohpcd binaries (zero source rebuilds).
- qtpaths and the test executables require a compatible `libc++_shared.so`:
  the device LD_LIBRARY_PATH contains an incompatible bundle copy, so the
  recipe prepends the qtbase lib dir and `/system/lib64` (bluez-qt 6.28.0
  precedent) both for the build environment and the test_package runtime.
- Build-tree tests link the generated KTextTemplate plugin into
  `kf6/ktexttemplate`, matching the installed plugin layout expected by the
  loader.
- The optional `ktexttemplate_scriptabletags` library is not registered because
  the verified `ktexttemplate` package for this chain is built without Qt QML
  support and does not install that plugin.
- The current `libxml2` baseline is library-only and does not provide
  `xmllint`; the upstream render-validation function is excluded from the final
  upstream test pass until that command is available.
- Runtime verification prepares `DT_NEEDED` compatibility links for KF
  dependencies that were published without SONAME and therefore can reference
  stale Conan cache paths in their dynamic sections.

## Verification

OHOS `conan create` passed (2026-09-09, recipe
bcb00199c28078a59bd3970cfe340dd0, package
aef545a367bda6f3aedc5e047d2aa6f9e0b1e5cd):

- Upstream CTest: 1/1 executed test passed
  (`grantleetheme-grantleethememanagertest`).
- Additional upstream QtTest subset: 7 checks passed from `grantleethemetest`
  (`shouldHaveDefaultValue`, `shouldInvalidWhenPathIsNotValid`,
  `shouldLoadTheme` data rows).
- `test_package`: 1/1 passed, including installed
  `KPim6::GrantleeTheme` CMake discovery, link, and direct render smoke
  (rendered `Hello Akonadi`).
- The dependency graph resolves every dependency to a published ohpcd binary;
  only grantleetheme itself is built from source.

Not executed:

- `GrantleeThemeTest::testRenderTemplate` uses the external `xmllint` command
  to validate and format generated HTML before comparing expected output. The
  current `libxml2` baseline is built with programs disabled, and no `xmllint`
  command is available in the OHOS packaging profile, so this upstream
  validation function is a hard toolchain block. The package consumer smoke
  still verifies installed-library rendering without altering upstream
  templates.
- `appstreamcli` validation is optional and is not registered because the tool
  is unavailable in the OHOS packaging profile.
- `ECMCheckOutboundLicense`/ReuseTool checks are optional and are not registered
  because `reuse` is unavailable in the OHOS packaging profile.
- Qt Assistant documentation targets are disabled with `BUILD_QCH=OFF`.
