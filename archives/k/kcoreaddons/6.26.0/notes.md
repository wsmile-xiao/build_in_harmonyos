# kcoreaddons 6.26.0 notes

## Scope

This package is part of the Akonadi KF 6.18 baseline. It updates the
published 6.14.0 HarmonyOS PC recipe to KDE Frameworks 6.26.0 while keeping
the core library surface minimal.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `KCOREADDONS_USE_QML=OFF` disables the optional QML plugin; Akonadi needs
  `KF6::CoreAddons`, not the QML plugin.
- `BUILD_TESTING=ON` runs the upstream CTest autotests during Conan build.
- `ecm_install_po_files_as_qm(poqm)` is disabled because the Qt Linguist tools
  component is not part of the qtbase package used by this repository.
- `src/lib/CMakeLists.txt` treats OHOS as a non-Windows Unix-like platform for
  `*_unix.cpp` source selection.
- Additional OHOS autotest fixes cover `dladdr` detection, missing MIME
  database compound archive suffixes, `LANGUAGE` locale fallback, and runtime
  skips when the current test filesystem lacks hardlinks or user/group
  database entries.

## Verification

Initial local checks:

- Upstream source SHA256 verified:
  `e1d03cfc7d45987ec31f31104f4732812980e0038beab222633da1108eb6f42f`.
- The OHOS patches were checked against the unpacked 6.26.0 source, including
  the HarmonyOS clockskew engine source-selection patch and upstream autotest
  fixes.

OHOS `conan create` verification passed on 2026-08-19.

- Run directory: `/storage/Users/currentUser/ohos-test-runs/codex-a-kf618-upstream-kcoreaddons-r2-20260819-050553-48687`.
- Full package reference: `kcoreaddons/6.26.0#b4083157fce76aab1353c07296c63127:57ffd8c720a5bfee7e8827990cd6550a49181c1b#bbd8fcceff8a3e619c398e469a1ae5d2`.
- Upstream CTest: 30/30 passed.
- Conan `test_package`: 1/1 passed.
