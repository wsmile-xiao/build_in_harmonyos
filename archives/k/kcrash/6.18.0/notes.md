# kcrash 6.18.0 notes

## Scope

This package is part of the Akonadi KF 6.18 baseline. It updates the existing
HarmonyOS PC recipe from 6.14.0 to KDE Frameworks 6.18.0 and switches the KF
dependency to `kcoreaddons/6.18.0`.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `BUILD_DESIGNERPLUGIN=OFF` avoids Qt6UiPlugin/Qt Designer plugin discovery.
- `BUILD_TESTING=ON` enables the upstream CTest/autotests suite during the
  OHOS Conan package build.
- No source patch is required for the initial 6.18.0 recipe.

## Verification

Initial local checks:

- Upstream source SHA256 verified:
  `a66293821b151f575fcfb59848578749e248c5baa2f262ac86725d0f64b324e0`.

OHOS `conan create` verification passed on 2026-08-19.

- Runner log: `/storage/Users/currentUser/ohos-users/codex-a/kf618-kitemviews-upstream-low-20260819/logs/kcrash-r1.log`.
- Full package reference: `kcrash/6.18.0#8c40d6edb0f6e16217e2e7f991df6d71:b59c4a90bca3e3316d756bdd3265a0bb3881732c#f5ae9fafdad5d00062710c65fe090b81`.
- Runner results: L0 pass, L1 pass, L5 pass; L2 skip: no bin/ dir; L4 pass.
- Upstream CTest passed 3/3: `kcrashtest`, `coreconfigtest`, and
  `metadatatest`.
- Conan `test_package` passed 1/1 with a `KCrash::setDrKonqiEnabled(false)`
  consumer compile/link/runtime smoke.
