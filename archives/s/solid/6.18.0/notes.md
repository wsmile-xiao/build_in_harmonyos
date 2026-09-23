# solid 6.18.0 notes

## Scope

This recipe upgrades the Solid dependency needed by KIO 6.18.0 for the Akonadi
downstream package chain.

## Adaptations

- `USE_DBUS=OFF` and `UDEV_DISABLED=ON` keep the package on the fake hardware
  backend available in the current OHOS baseline.
- Translation catalog generation is disabled because the current Qt package
  set does not provide Qt6LinguistTools.
- The non-Linux fallback `fstab` backend is not built on OHOS.

## Verification

- Local pre-PR checks on 2026-08-31: `python -m py_compile` for the recipe and
  test recipe passed, and `conan export` succeeded with Conan home inside the
  workspace.
- OHOS real-device `conan create` was not rerun because the test device is
  currently unavailable; PR CI is expected to provide the package build result.
- PR CI builds #35382 and #35401 reached CMake configure and failed while
  running the build-context `flex --version` check because the already-published
  `flex/2.6.4` package does not contain `bin/flex`. The recipe now requires
  `flex/2.6.4.1`, which republishes the tool package with the executable, and
  keeps the build tool environment for `bison`, `flex`, and `m4` during
  `cmake.configure()` so their `bin` and `lib` directories are available to
  CMake's `FindFLEX`/`FindBISON`.
