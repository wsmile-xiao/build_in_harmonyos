# kcodecs 6.18.0 notes

## Scope

This package is part of the Akonadi KF 6.18 baseline and is required by
`kconfigwidgets/6.18.0`. The mainline `kcodecs/6.26.0` directory currently
contains only a report file, so a usable 6.18.0 recipe is needed.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `BUILD_TESTING=ON` runs the upstream CTest autotests during Conan build.
- `BUILD_FUZZERS=OFF` keeps oss-fuzz helper targets out of the package build.
- `ecm_install_po_files_as_qm(poqm)` is disabled because the Qt Linguist tools
  component is not part of the qtbase package used by this repository.
- `libiconv/1.17` is used as a legacy charset fallback because the OHOS
  qtbase package is built without ICU.

## Verification

Initial local checks:

- Upstream source SHA256 verified:
  `247eda9ade502699062c7baaca7bb93691a308f202c165954652875ebe777426`.
- The CMake and codec fallback patches were checked against the unpacked
  6.18.0 source.

OHOS `conan create` verification passed on 2026-08-19.

- Run directory: `/storage/Users/currentUser/ohos-test-runs/codex-a-kf618-upstream-kcodecs-r3-20260819-032954-5154`.
- Full package reference: `kcodecs/6.18.0.1#d905fd7bb3aa4f8a25eb908552615f32:546f25c40e62843f04e563647cb09d4d09d8b48c#d8fa20d70ead0fff3348f8d2ef686109`.
- Upstream CTest: 6/6 passed.
- Conan `test_package`: 1/1 passed.
