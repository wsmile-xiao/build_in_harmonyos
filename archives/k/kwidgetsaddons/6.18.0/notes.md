# kwidgetsaddons 6.18.0 notes

## Scope

This package is part of the Akonadi KF 6.18 baseline. It updates the existing
HarmonyOS PC recipe from 6.14.0 to KDE Frameworks 6.18.0.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `BUILD_PYTHON_BINDINGS=OFF` is required for 6.18.0 because Python bindings
  otherwise default to ON and try to discover Shiboken6/PySide6.
- `BUILD_DESIGNERPLUGIN=OFF` avoids Qt6UiPlugin/Qt Designer plugin discovery.
- `BUILD_TESTING=ON` runs the upstream CTest autotests during Conan build.
- The OHOS headless runner excludes `ktooltipwidgettest` and
  `kwidgetsaddons-kcolumnresizertest`: the first hangs under the offscreen
  platform plugin, and the second asserts native layout geometry that differs
  under offscreen.
- `ecm_install_po_files_as_qm(poqm)` is disabled because the Qt Linguist tools
  component is not part of the qtbase package used by this repository.

## Verification

Initial local checks:

- Upstream source SHA256 verified:
  `0c2fb00744ffd9ecb7531ee5a79c1db4b406753f250565122f3add93cf200afb`.
- The po/qm patch was checked against the unpacked 6.18.0 source.

OHOS `conan create` verification passed on 2026-08-19.

- Run directory: `/storage/Users/currentUser/ohos-test-runs/codex-a-kf618-upstream-kwidgetsaddons-r2-20260819-043935-56877`.
- Full package reference: `kwidgetsaddons/6.18.0#14f804f3a723d9aa7f3bf75bf1889e19:57ffd8c720a5bfee7e8827990cd6550a49181c1b#6158d48b2b6bab8e8dce04003194b4bb`.
- Upstream CTest: 23/23 executed tests passed.
- Excluded upstream CTest entries: `ktooltipwidgettest`,
  `kwidgetsaddons-kcolumnresizertest`.
- Conan `test_package`: 1/1 passed.
