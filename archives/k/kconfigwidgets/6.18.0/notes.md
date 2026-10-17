# kconfigwidgets 6.18.0 notes

## Scope

This package is part of the Akonadi KF 6.18 baseline. It is based on the
existing remote 6.14.0 recipe and adds a mainline-ready 6.18.0 package
directory without modifying the 6.14.0 branch.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `USE_DBUS=OFF` avoids Qt6DBus until the shared Qt DBus baseline lands.
- `BUILD_DESIGNERPLUGIN=OFF` avoids Qt6UiPlugin.
- `BUILD_TESTING=ON` enables the upstream CTest/autotests suite during the
  OHOS Conan package build.
- `KF_SKIP_PO_PROCESSING=ON` avoids translation catalog generation in the
  cross-build package path.
- Runtime/build dependencies are aligned to the KF 6.18 baseline, including
  the newly added `kcodecs/6.18.0`.

## Verification

Initial local checks:

- Upstream source SHA256 verified:
  `aa5a7be6278a19733f77e6a435f84c3e71926b28f1ac3766313778890d640813`.
- No source patch is required for the 6.18.0 minimal OHOS baseline.

OHOS `conan create` verification passed on 2026-08-19.

- Runner log: `/storage/Users/currentUser/ohos-users/codex-a/kf618-kitemviews-upstream-low-20260819/logs/kconfigwidgets-botfix-r1.log`.
- Full package reference: `kconfigwidgets/6.18.0#1b8f807a37bd7aca702d599e843a00fa:ed90bbd1469dae72bf80afb5a2f6fd37a3a67109#e060cda7424b325f466a80f7863d7bd1`.
- Runner results: L0 pass, L1 pass, L5 pass; L2 skip: no bin/ dir; L4 pass.
- Upstream CTest passed 7/7: `kstandardactiontest`,
  `kconfigdialog_unittest`, `klanguagenametest`, `kcmdbartest`,
  `khamburgermenutest`, `krecentfilesaction_test`, and `kopenaction_test`.
- Conan `test_package` passed 1/1 with a real `KConfigDialog` consumer smoke:
  it constructs the dialog, verifies `exists()` registration, adds a page,
  checks `currentPage()`, and verifies teardown unregisters the dialog.
