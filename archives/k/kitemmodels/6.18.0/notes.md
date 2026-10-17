# kitemmodels 6.18.0 notes

## Scope

This package is part of the Akonadi KF 6.18 baseline. It adds the previously
missing KDE Frameworks ItemModels package for HarmonyOS PC.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `BUILD_TESTING=ON` runs the upstream CTest autotests during Conan build.
- The recipe depends only on `qtbase/6.11.1`; upstream `Qt6Qml` support is
  optional and is skipped for the first Akonadi baseline.
- No source patch is required for the initial 6.18.0 recipe.

## Verification

Initial local checks:

- Upstream source SHA256 verified:
  `887653b1571ad0afd4b836ad2451a42b07657d0eede1a2628e9c69102ce23de1`.

OHOS `conan create` verification passed on 2026-08-19.

- Runner log: `/storage/Users/currentUser/ohos-users/codex-a/kf618-kitemviews-upstream-low-20260819/logs/kitemmodels.log`.
- Full package reference: `kitemmodels/6.18.0#2310802ce337cba89af05c59ddf4045c:57ffd8c720a5bfee7e8827990cd6550a49181c1b#2e418627a6cf70d2f827b904a8b2f3d9`.
- Upstream CTest: 10/10 passed.
- Conan `test_package`: 1/1 passed.
- Runner results: L0 pass, L1 pass, L4 pass, L5 pass; L2 skip: no bin/ dir; `RUN_RC=0`.
