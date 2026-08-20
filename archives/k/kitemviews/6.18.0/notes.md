# kitemviews 6.18.0 notes

## Scope

This package is part of the Akonadi KF 6.18 baseline. It updates the existing
HarmonyOS PC recipe from 6.14.0 to KDE Frameworks 6.18.0.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `BUILD_DESIGNERPLUGIN=OFF` avoids Qt6UiPlugin/Qt Designer plugin discovery.
- `BUILD_TESTING=ON` runs the upstream CTest autotest during Conan build.
- `ecm_install_po_files_as_qm(poqm)` is disabled because the Qt Linguist tools
  component is not part of the qtbase package used by this repository.

## Verification

Initial local checks:

- Upstream source SHA256 verified:
  `f74c03e2ec367238ec395b1f2438878999c2be3e29b41b6bd4a3ccd04440e29a`.
- The po/qm patch was checked against the unpacked 6.18.0 source.

OHOS `conan create` verification passed on 2026-08-19.

- Runner log: `/storage/Users/currentUser/ohos-users/codex-a/kf618-kitemviews-upstream-low-20260819/logs/kitemviews-r1.log`.
- Full package reference: `kitemviews/6.18.0#516377104efd59c8bf91017d8a234897:57ffd8c720a5bfee7e8827990cd6550a49181c1b#9bbefdca2020ac0ec4e0df6d9c2fb7ba`.
- Upstream CTest: 1/1 passed.
- Conan `test_package`: 1/1 passed.
- Runner results: L0 pass, L1 pass, L4 pass, L5 pass; L2 skip: no bin/ dir;
  `RUN_RC=0`.
