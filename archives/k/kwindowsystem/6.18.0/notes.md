# kwindowsystem 6.18.0 notes

## Scope

This package is part of the Akonadi KF 6.18 baseline. It updates the existing
HarmonyOS PC recipe from 6.14.0 to KDE Frameworks 6.18.0.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `KWINDOWSYSTEM_QML=OFF` disables optional QML bindings.
- `KWINDOWSYSTEM_X11=OFF` and `KWINDOWSYSTEM_WAYLAND=OFF` avoid unavailable
  X11/Wayland stacks on OHOS.
- `BUILD_DESIGNERPLUGIN=OFF` avoids Qt6UiPlugin/Qt Designer plugin discovery.
- `BUILD_TESTING=ON` runs the upstream CTest autotests registered by the
  current headless feature set.
- `ECMQmlModule` include and `ecm_install_po_files_as_qm(poqm)` are disabled
  by patch for the minimal OHOS baseline.

## Verification

Initial local checks:

- Upstream source SHA256 verified:
  `a0a046039a11baebacd96d836e5765b981426f60d2cea9ff9a99ba8dbe56178e`.
- The CMake patch was checked against the unpacked 6.18.0 source.

OHOS `conan create` verification passed on 2026-08-19.

- Run directory: `/storage/Users/currentUser/ohos-test-runs/codex-a-kf618-upstream-kwindowsystem-r1-20260819-051120-64054`.
- Full package reference: `kwindowsystem/6.18.0#ab0426f028c0f4314d8259f074976ec6:57ffd8c720a5bfee7e8827990cd6550a49181c1b#8fab81c14d38d69659691752a29abee4`.
- Upstream CTest: 1/1 passed.
- Conan `test_package`: 1/1 passed.
