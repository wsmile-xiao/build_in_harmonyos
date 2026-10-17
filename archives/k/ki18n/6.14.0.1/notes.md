# ki18n 6.14.0.1 notes

## Scope

Fix task contrib-3768 (platform branch `fix/ki18n-6.14.0`). ki18n 6.14.0 was
published on 2026-08-10 as a reduced build: `BUILD_WITH_QML=OFF` (qtdeclarative
was not published at the time) and `BUILD_TESTING=OFF`. This revision
backports the 6.18.0.1 fix to 6.14.0 now that its prerequisites are published:

- `qtdeclarative/6.11.1` is in ohpcd → `BUILD_WITH_QML=ON` ships the QML
  i18n add-on (`KF6I18nQml` / `libKF6I18nQml.so`, `KLocalizedQmlContext`)
  plus the localedata QML plugin.
- `gettext/0.22.5.1` (with msgfmt) is in ohpcd → `BUILD_TESTING=ON` runs the
  upstream CTest autotests during the Conan build.

Version is bumped 6.14.0 → 6.14.0.1 per R37 (the artifact registry does not
host multiple revisions of the same version; PR-stage L0j blocks same-version
recipe modifications).

## Branch naming note

The platform task requires the branch `fix/ki18n-6.14.0` (changeType=fix,
L0n allows `fix/` prefix + exact `name-version`), while the archive directory
and conan version are `6.14.0.1` (R37 version increment). This difference is
intentional and matches the 6.18 precedent (`fix` branch name carries the
upstream base version, the archive carries the bumped fix revision).

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `BUILD_WITH_QML=ON` enables the scripted translation support (Qt6Qml),
  provided by the published qtdeclarative/6.11.1 split package. This is the
  main delta vs published 6.14.0.
- `BUILD_TESTING=ON` + `ctest` execution in `build()`: upstream autotests run
  on OHOS (same runner as 6.18.0.1, incl. QML2_IMPORT_PATH wiring to
  qtdeclarative `<pkg>/qml` so the QML engine finds `QtQml`).
- `KF_SKIP_PO_PROCESSING=ON` avoids building translation catalogs in the
  cross-build package path.
- `gettext/0.22.5.1` remains required for `LibIntl`, which the library links
  against on non-glibc platforms; msgfmt from the same package serves the
  `ki18n_install` autotest.
- `ecm/6.26.0` (6.18.0.1's tool_requires; ECM is backward compatible with
  ki18n 6.14 — 6.14.0 originally used ecm/6.20.0, both are published; W0
  verified both; the 6.26.0 choice keeps parity with the 6.18.0.1 reference
  recipe).
- `KF6I18nMacros.cmake.in` is patched so consumers are not forced to find the
  Gettext command-line tools when only linking `KF6::I18n` (verified: the
  patch applies cleanly to the 6.14.0 tarball, the file content is identical
  around the hunk).

## Verification

Pre-checks (2026-09-02):

- W0 dependency probe (`conan download <pkg> -r=ohpcd --only-recipe`):
  qtbase/6.11.1 ✅, qtdeclarative/6.11.1 ✅, gettext/0.22.5.1 ✅,
  ecm/6.26.0 ✅ (ecm/6.20.0 also verified published).
- Upstream source SHA256 verified:
  `2a5135412caf0a07eba4eeb60867ac6929df1c83c145ae757a6a1230f842e669`.
- Patch dry-run against the unpacked 6.14.0 source: applies cleanly.
- 6.14.0 autotests layout matches 6.18.0 (same test set incl.
  ki18ndeclarativetest behind BUILD_WITH_QML, same four locale-data tests
  requiring iso-codes).

W3 `conan create` verification (2026-09-02, ohos-aarch64 profile, `--user=ohpcd --channel=stable`):

```
ki18n/6.14.0.1@ohpcd/stable: Excluding upstream tests requiring unavailable
  OHOS iso-codes data: kcatalogtest, kcountrytest, kcountrysubdivisiontest, ktimezonetest
100% tests passed, 0 tests failed out of 12     (incl. Test #1 ki18ndeclarativetest, the QML engine test)
test_package: PASS: ki18n core + QML add-on API exercised
Full package reference: ki18n/6.14.0.1@ohpcd/stable#32255c4d1e67454576359f5d0945518d:01fcafe7f6bbeadd23b6c4c94166b26db869f529#660bc4c98fed23ad6f5ddd7217b2ccc8
```

New artifacts vs published 6.14.0: `libKF6I18nQml.so` (KF6I18nQml add-on)
+ `lib/qml/org/kde/i18n/localeData/` QML module (`libKF6LocaleDataQml.so`
plugin). Core `libKF6I18n.so`/`libKF6I18nLocaleData.so` unchanged.

Environment note (device quirk, same class as the known subprocess PATH
issue): running `conan create` from an OpenDesk desktop session inherits a
polluted `LD_LIBRARY_PATH` (contains whitespace-only entries), which makes
musl fail to load `libc++_shared.so` for qtbase's qtpaths during ECM's
`ecm_query_qt` → configure aborts with "Qt6 qtpaths call failed: 127". Fix:
run under a clean env (`env -u LD_LIBRARY_PATH`); the CI runner env is clean
so this is a local-device-only trap (documented here for future fix tasks).
---

**编译结束**: 2026-09-03 00:29
**最终状态**: built
