# kcompletion 6.26.0 notes

## Scope

This package is part of the KF 6.26 baseline (task 6327, KF6 chain layer 3).
It adds a mainline-ready `kcompletion/6.26.0` package directory without
modifying other KF package recipes. Version follow-up from the 6.18.0
recipe: same OHOS adaptation set, dependencies bumped to the 6.26.0 KF
baseline.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `BUILD_DESIGNERPLUGIN=OFF` avoids Qt6UiPlugin/Qt Designer plugin discovery.
- `KF_SKIP_PO_PROCESSING=ON` avoids translation catalog generation
  (Qt6LinguistTools is not published to ohpcd).
- `BUILD_TESTING=ON` enables the upstream CTest/autotests suite during the
  OHOS Conan package build.
- Runtime/build dependencies use the KF 6.26 baseline:
  `kcodecs/6.26.0`, `kconfig/6.26.0`, and `kwidgetsaddons/6.26.0`.
- E132: the OHOS SDK `llvm/lib` dir is prepended to `LD_LIBRARY_PATH` for the
  build and test steps (lld needs `libxml2.so.16` shipped there; kconfig
  6.26.0 precedent). `/system/lib64` is prepended as well so the compatible
  `libc++_shared.so` resolves before the incompatible sandbox copy under
  `/data/storage/el1/bundle/libs/arm64` (bluez-qt 6.28.0 precedent).

## Verification

Initial local checks:

- Upstream source SHA256 verified on the OHOS runner:
  `95f71eb807e4de40ecdfe7234c9c3d844423171ac52588aecca642f78d904e48`.
- Upstream v6.26.0 tag confirmed on
  https://invent.kde.org/frameworks/kcompletion (commit
  3bcc8d95c960c71cea26737088b4aae8332547f6).
- No source patch is required for the 6.26.0 OHOS baseline
  (`cmake_minimum_required(VERSION 3.29)` is satisfied by the runner's
  CMake 4.1.2).
