# kcolorscheme 6.18.0 notes

## Scope

This package is part of the Akonadi KF 6.18 baseline. It is based on the
existing remote 6.14.0 recipe and adds a mainline-ready 6.18.0 package
directory without modifying the 6.14.0 branch.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `KF_SKIP_PO_PROCESSING=ON` avoids translation catalog generation in the
  cross-build package path.
- `BUILD_TESTING=ON` enables the upstream CTest/autotests suite during the
  OHOS Conan package build.
- Runtime/build dependencies are aligned to the KF 6.18 baseline:
  `kconfig/6.18.0`, `kguiaddons/6.18.0`, and `ki18n/6.18.0`.
- Upstream requires `Qt6GuiPrivate` when Qt6Gui is 6.10 or newer; this is
  expected to come from `qtbase/6.11.1`.

## Verification

Initial local checks:

- Upstream source SHA256 verified:
  `14e99e74cc636640ac8d705f2878d72d0379fff671e75c0f138302489898d651`.
- No source patch is required for the 6.18.0 minimal OHOS baseline.

OHOS `conan create` verification passed on 2026-08-19.

- Runner log: `/storage/Users/currentUser/ohos-users/codex-a/kf618-kitemviews-upstream-low-20260819/logs/kcolorscheme-r2.log`.
- Full package reference: `kcolorscheme/6.18.0#43b1e2bcfcefc51b5619858b6316f5ff:742b53369c1b9ae12f3c09d348f766caa772598a#c5789ec1c12eb74c7fa7295590b1fc20`.
- Runner results: L0 pass, L1 pass, L5 pass; L2 skip: no bin/ dir; L4 pass.
- Upstream CTest passed 1/1: `kcolorschemetest`.
- Conan `test_package` passed 1/1 with a `KColorScheme` consumer smoke that
  constructs the scheme and verifies a valid background brush.
