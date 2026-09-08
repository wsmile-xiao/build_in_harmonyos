# kitemviews 6.26.0 notes

## Scope

This package is part of the KF6 6.26 baseline (task #6323, dependency chain:
extra-cmake-modules 6.26.0 + qtbase 6.11.1). It updates the existing
HarmonyOS PC recipe from 6.18.0 to KDE Frameworks 6.26.0.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `BUILD_DESIGNERPLUGIN=OFF` avoids Qt6UiPlugin/Qt Designer plugin discovery.
- `BUILD_TESTING=ON` runs the upstream CTest autotest during Conan build.
- `ecm_install_po_files_as_qm(poqm)` is disabled because the Qt Linguist tools
  component is not part of the qtbase package used by this repository.
- ECM 6.26 KDEInstallDirs6 runs the qtbase `qtpaths` host tool during
  configure; the sandbox LD_LIBRARY_PATH contains an incompatible
  libc++_shared.so which shadows the compatible one, so `/system/lib64` and
  the qtbase lib dir are prepended (kconfig 6.26.0 / bluez-qt 6.28.0
  precedent).

## Verification

Initial local checks:

- Upstream source SHA256 verified:
  `e76cc9d7561d0aae22b07a77552fbcddf61c8066bac5cfac9958ac065b617e74`.
- The po/qm patch was verified to apply cleanly against the unpacked 6.26.0
  source with patch_ng (the same engine conan uses); the only upstream change
  near the patch context is the Qt deprecation version line (6.9/6.10 -> 6.11).

OHOS `conan create` verification passed on 2026-09-05.

- Runner log: `~/tmp/kitemviews-create-r1.log` (local W3 run).
- Full package reference:
  `kitemviews/6.26.0#e2d9c7810e85761be26fdafba1b54042:57ffd8c720a5bfee7e8827990cd6550a49181c1b#6b2d0d9d189282a14d6055e46e07cbb5`.
- Upstream CTest: 1/1 passed (kitemviews-klistwidgetsearchlinetest).
- Conan `test_package`: 1/1 passed.
- Runner results: L0 pass, L1 pass, L4 pass, L5 pass; L2 skip: no bin/ dir
  (library only).

