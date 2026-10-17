# eigenpy 3.13.0 OHOS pre-adaptation notes

## Status

Prepared local Conan recipe and non-stub test_package in
`archives/e/eigenpy/3.13.0/`.

Current status is ready for PR CI refresh after successful device shadow CI:

- Windows host uses Conan 2.29.1 from
  `C:\Users\ASUS\AppData\Roaming\Python\Python312\Scripts\conan.exe`.
- `boost/1.90.0.2.1` has been merged into upstream main with Boost.Python
  components (`python`, `python3`, `python312`) and official CI #32770 passed.
- The eigenpy recipe now pins `boost/1.90.0.2.1` and still fails early with
  `ConanInvalidConfiguration` if the resolved Boost package lacks
  `libboost_python312`, `libboost_python3`, or `libboost_python`.
- `package_info()` exports a direct `boost::python312` component requirement so
  downstream CMakeDeps consumers inherit the actual Boost.Python link target.
- On OHOS, the recipe preloads both legacy `PYTHON_*` and modern
  `Python`/`Python3` CMake variables so Boost.Python's nested
  `find_dependency(Python ...)` resolves the same Python 3.12 installation.
- Official CI may provide CPython headers without an installed NumPy module; the
  recipe extracts NumPy 2.5.1 generated C headers from the pinned Python 3.12
  aarch64 wheel and uses a tiny configure-only stub for CMake's
  `numpy.get_include()` probe.
- On OHOS, the recipe patches eigenpy's main library and `eigenpy_pywrap`
  targets to link the discovered `libpython3.12.so`; this satisfies lld's
  undefined-symbol checks for Boost.Python users.

Per the one-library/one-PR rule, the Boost.Python dependency work stays in the
separate Boost PR. This package only consumes the merged dependency.

Issue tracking was intentionally skipped per current task instruction.

## Source

Primary source:

- URL: `https://files.pythonhosted.org/packages/source/e/eigenpy/eigenpy-3.13.0.tar.gz`
- SHA256: `49d3cb46b85696baf5445ac707b48aade07c21579c188dfc1c8ad2f92e05fab5`

Submodule source:

- Upstream `v3.13.0` records `cmake/` as jrl-cmakemodules commit
  `f07de7952b35caf1c7a53a49138772cb9c534cf5`.
- URL list: gh-proxy GitHub archive mirror first, then GitHub codeload.
- SHA256: `e428b43dd2379fa1af64f48fc99d867b1deaa2dc97a6f6d50759f06a21cc0902`

NumPy header source:

- URL: `https://files.pythonhosted.org/packages/a9/4b/a2b32dd94ee9ffbeecb28152240042a3949db33b1c834d44090b80e1b3b8/numpy-2.5.1-cp312-cp312-manylinux_2_27_aarch64.manylinux_2_28_aarch64.whl`
- SHA256: `61ac47e772e6b8ea489e1d2f441a34c5c3ac17327e7ce294cbdf535795ad4e75`
- Purpose: generated C headers only; the wheel binary modules are not packaged
  or imported at runtime.

## Build system analysis

eigenpy is a CMake project (`cmake_minimum_required(VERSION 3.22)`) using
jrl-cmakemodules. The PyPI sdist contains `.gitmodules` but not the actual
`cmake/` submodule contents, so the recipe downloads the exact submodule commit
into `cmake/` during `source()`.

Required dependencies observed in upstream files:

- `Eigen3`, minimum declared by CMake as `eigen3 >= 3.0.5`; recipe uses
  `eigen/3.4.0`.
- `Boost` plus `Boost.Python`; recipe uses the Boost.Python-enabled
  `boost/1.90.0.2.1` package.
- Python interpreter, Python development headers, and NumPy headers.
- jrl-cmakemodules submodule for build macros.

Optional features disabled for the first OHOS pass:

- `BUILD_TESTING_SCIPY=OFF`
- `BUILD_WITH_CHOLMOD_SUPPORT=OFF`
- `BUILD_WITH_ACCELERATE_SUPPORT=OFF`
- `GENERATE_PYTHON_STUBS=OFF`
- `INSTALL_DOCUMENTATION=OFF`

## Upstream tests

`unittest/CMakeLists.txt` registers about 20 compiled/import module tests and
52 Python unit tests. The source tree contains 73 files under `unittest/`.

The recipe currently configures `BUILD_TESTING=OFF` for the first renewed OHOS
pass so dependency discovery and install layout can be stabilized first. After
`conan create` and the consumer test pass, re-enable a selected upstream CTest
subset in `build()` where feasible. If hmdfs blocks Python `dlopen`, use the
same classification as the Boost.Python dependency PR and document the E212
fallback rather than treating it as a source build failure.

## test_package

The test package is intentionally non-stub:

- `test_version.cpp` links against `libeigenpy` and checks
  `eigenpy::printVersion()` / `eigenpy::checkVersionAtLeast()`.
- `test_import.py` imports the installed Python package, checks `__version__`,
  calls `checkVersionAtLeast()`, and exercises `is_approx()` with NumPy arrays.

On OHOS, the test signs the C++ executable before running and prepends the
package dependency library directories plus the device Python runtime library
directory to `LD_LIBRARY_PATH`. If Python `dlopen` from the runner path is
blocked by platform policy, the test falls back to static ELF inspection of the
installed `eigenpy_pywrap` extension and records that as an OHOS loader-policy
issue.

## Validation performed

- Created isolated worktree `D:\harmonyos\worktrees\eigenpy` on branch
  `feat/eigenpy-3.13.0`.
- Main source tarball downloaded and SHA256 verified locally.
- jrl-cmakemodules submodule commit resolved through GitHub contents API and
  tarball SHA256 verified locally.
- Upstream build files inspected: `CMakeLists.txt`, `python/CMakeLists.txt`,
  `unittest/CMakeLists.txt`, `package.xml`, jrl `python.cmake`, jrl
  `boost.cmake`.
- `python -B -m py_compile` passed for the recipe and test_package.
- YAML parsing passed for `manifest.yaml`, `conandata.yml`,
  `test_package/MANIFEST.yml`, and the eigenpy knowledge draft.
- `git diff --check` passed for the eigenpy archive and direct knowledge draft.
- Isolated W0 dependency checks with
  `CONAN_HOME=D:\harmonyos\worktrees\eigenpy\.conan-w0`:
  `conan download eigen/3.4.0 -r=ohpcd --only-recipe` passed, and
  `conan download boost/1.90.0.2.1 -r=ohpcd --only-recipe` passed.
- `conan download eigenpy/3.13.0 -r=ohpcd --only-recipe` hit the remote-side
  response `error:system acceleration policy not enabled`, so the duplicate
  version check is left for official CI.
- `conan export . --user=ohpcd --channel=stable` passed for the local recipe.
- `conan graph info . --user=ohpcd --channel=stable --format=json` resolved the
  dependency graph with `eigen/3.4.0` and `boost/1.90.0.2.1`; Windows package
  validity failed only because the detected host profile has no compiler.
- `conan source` passed in a temporary source-check directory after listing the
  verified gh-proxy jrl-cmakemodules archive before direct GitHub codeload.
- Older shadow CI on the HarmonyOS device reached `build()` after simulating PR
  diff mode with a temporary `pr.diff` in the manual clean1 work directory.
- Older shadow CI run:
  `/storage/Users/currentUser/ohos-test-runs/codex-eigenpy-eigenpy-3.13.0-C0DX-shadow-20260825-222748-25523`.
  Result: `rc=1`, superseded dependency blocker. `conan create` reached
  `build()` and failed with `ConanInvalidConfiguration` because
  `boost/1.90.0.2` did not contain `libboost_python312.so`,
  `libboost_python3.so`, or `libboost_python.so`.
- 2026-08-29: worktree fast-forwarded to upstream AtomGit main
  `53e4f32fa6`, which contains merged `boost/1.90.0.2.1`; recipe and metadata
  updated to consume that dependency.
- 2026-08-29: direct GitHub codeload for the 6.1MB jrl-cmakemodules submodule
  was too slow in local source verification (timed out after 60s at about
  1.2MB). The gh-proxy GitHub archive mirror completed in about 10s and matched
  the pinned SHA256, so it is listed first with codeload as fallback.
- 2026-08-29: added direct eigenpy knowledge drafts for Boost.Python component
  linkage and OHOS test_package loader fallback so the PR body can cite the
  exact recovery patterns used here.
- 2026-08-29: device shadow CI passed after adding Python CMake cache hints,
  explicit `libpython3.12.so` linkage for both eigenpy CMake targets, and
  Python runtime `LD_LIBRARY_PATH` setup in `test_package`.
  Run directory:
  `/storage/Users/currentUser/ohpc-ci-shadow/runs/20260829T024352Z-578938555d-51375`.
  Results: `G0_RESULT=pass`, `L0_RESULT=pass`, `L1_RESULT=pass`,
  `L2_RESULT=skip`, `L4_RESULT=pass`, `L5_RESULT=pass`.
- 2026-08-29: official CI #34221 reproduced a worker environment where
  `/data/service/hnp/bin/python3.12` exists but `import numpy` fails. Added the
  pinned NumPy header wheel fallback and changed OHOS `test_package` import
  fallback to classify missing runtime NumPy as an environment limitation after
  static ELF inspection.
- 2026-08-29: official CI #34231 then reached link and failed with
  `ld.lld: error: unable to find library -lintl` from Python's imported CMake
  target. The OHOS patch now links the discovered `libpython3.12.so` file via
  `OHOS_PYTHON_LIBRARY` before falling back to `Python::Python`.
- 2026-08-29: official CI #34250 progressed past the `-lintl` link failure but
  hit the 3600s `conan create` timeout while building eigenpy's template-heavy
  CMake target set. The recipe now uses bounded CMake parallelism on OHOS
  (`tools.build:jobs`, default/cap 2) and selects Ninja when available so the
  package can fit the CI time budget without changing the installed ABI surface.

## Next commands

Run only the eigenpy package:

```sh
CI_PACKAGES="archives/e/eigenpy/3.13.0" \
CI_BRANCH="feat/eigenpy-3.13.0" \
zsh ci/conan/build_and_test.sh
```

Shadow CI equivalent:

```sh
sh "$HOME/bin/run-ohos-shadow-ci.sh" archives/e/eigenpy/3.13.0
```
