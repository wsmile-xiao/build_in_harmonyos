# ki18n 6.18.0 notes

## Scope

This package is part of the Akonadi KF 6.18 baseline. It updates the
published 6.14.0 HarmonyOS PC recipe to KDE Frameworks 6.18.0 while keeping
the core `KF6::I18n` library usable by downstream packages.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `BUILD_WITH_QML=OFF` avoids the optional scripted translation support that
  requires Qt6Qml.
- `KF_SKIP_PO_PROCESSING=ON` avoids building translation catalogs in the
  cross-build package path.
- `BUILD_TESTING=ON` runs the upstream CTest autotests during Conan build.
- The OHOS runner excludes `kcatalogtest`, `kcountrytest`,
  `kcountrysubdivisiontest`, and `ktimezonetest` because the optional
  upstream iso-codes runtime data is not currently available.
- `gettext/0.22.5.1` remains required for `LibIntl`, which the library links
  against on non-glibc platforms.
- `KF6I18nMacros.cmake.in` is patched so consumers are not forced to find the
  Gettext command-line tools when only linking `KF6::I18n`.

## Verification

Initial local checks:

- Upstream source SHA256 verified:
  `d0cbfbf3427c0368daa23f9f68b3cb5b03ad37b6820591491b3ea8a0a28bea61`.
- The consumer macro patch was checked against the unpacked 6.18.0 source.

OHOS `conan create` verification passed on 2026-08-19.

- Runner log: `/storage/Users/currentUser/ohos-users/codex-a/kf618-kitemviews-upstream-low-20260819/logs/ki18n-r2.log`.
- Full package reference: `ki18n/6.18.0.2#1afbd891a456acca910ee831b9bb0bfa:57ffd8c720a5bfee7e8827990cd6550a49181c1b#64f86e7ef65bd13ec11c41351509c644`.
- Upstream CTest: 9/9 executed tests passed.
- Excluded upstream CTest entries: `kcatalogtest`, `kcountrytest`,
  `kcountrysubdivisiontest`, `ktimezonetest`.
- Conan `test_package`: 1/1 passed.
- Runner results: L0 pass, L1 pass, L4 pass, L5 pass; L2 skip: no bin/ dir;
  `RUN_RC=0`.
