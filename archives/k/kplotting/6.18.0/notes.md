# kplotting 6.18.0 notes

## Scope

This package is part of the KF 6.18 baseline. It adds a mainline-ready
`kplotting/6.18.0` package directory without modifying other KF package
recipes.

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `BUILD_DESIGNERPLUGIN=OFF` keeps the optional Qt Designer plugin out of the
  cross-build baseline.
- `BUILD_TESTING=ON` enables the upstream Qt autotest suite during the OHOS
  Conan package build.
- Runtime/build dependencies use the current local baseline:
  `qtbase/6.11.1` and `ecm/6.26.0`.
- CMake configure/build prepends the OHOS SDK `native/llvm/lib` directory to
  `LD_LIBRARY_PATH` so SDK `lld` can load its matching `libxml2.so.16` on CI
  workers that do not export that path globally.

## Verification

Initial local checks:

- Upstream source SHA256 verified on the remote runner:
  `c9fdb99fd1c75f588e2f15ef84333feadf327a878c24324e44493d03e593ebc9`.
- `python -m py_compile` passed for the main recipe and `test_package`
  recipe.
- `git diff --check` passed.

OHOS low-pressure runner verification:

- Run log:
  `/storage/Users/currentUser/ohos-users/codex-a/kf618-kitemviews-upstream-low-20260819/logs/kplotting-r1.log`.
- Full package reference:
  `kplotting/6.18.0#2df9f46f047cc1d51bfbb5d593a6f3f2:57ffd8c720a5bfee7e8827990cd6550a49181c1b#b57be39d6fa7a9f9efa81816e9589aee`.
- L0: pass, all quality gate checks passed.
- L1: pass, upstream CTest and `test_package` both executed.
- L2: skip, no `bin/` directory is installed by this library package.
- L4: pass, no source patches are carried.
- L5: pass, installed `lib/` has content.
- Upstream CTest: 4/4 executed tests passed:
  `kplotpointtest`, `kplotaxistest`, `kplotobjecttest`, and
  `kplotwidgettest`.
- `test_package`: 1/1 passed, including CMake configure/build, CTest, and
  direct runtime smoke. The smoke validates KF6Plotting consumer compile/link
  and runtime loading through `KPlotWidget`, `KPlotObject`, and `KPlotPoint`
  with `QT_QPA_PLATFORM=offscreen`.

## Upstream tests not run

- None of the registered upstream CTest entries were skipped or excluded in the
  final verification.
- Optional Qt Designer plugin coverage is not applicable to this baseline
  package because the optional plugin is disabled with `BUILD_DESIGNERPLUGIN=OFF`.
  The upstream release does not register separate Designer plugin CTest entries.
- L2 version/help smoke is not run because this package installs a library and
  no `bin/` directory.
