# Morpheus 2.4.1 Upstream GTest OHOS Run

Date: 2026-08-02

## Scope

- Source under test: Morpheus upstream tag `v2.4.1`, commit `110278081c6b1b9a2a0113fbf19d390e37435814`.
- Test dependency: GoogleTest tag `v1.15.2`, commit `b514bdc898e2951020cbdca1304b75f5950d1f59`, built job-locally.
- OHOS profile: `ohos-aarch64`, same Morpheus dependency cache/profile as PR !3459 true-device validation.
- Morpheus configuration: CLI-only, `MORPHEUS_GUI=OFF`, `MORPHEUS_GRAPHVIZ=None`, `MORPHEUS_OPENMP=OFF`, `BUILD_TESTING=ON`.

## Harness Notes

- Applied the same Morpheus OHOS recipe source fixes used by the package build.
- Skipped upstream `3rdparty/GTest` network clone by using job-local GTest and `MORPHEUS_USE_SYSTEM_GTEST=ON`.
- Added an `xxd -i input output` compatibility wrapper because the device `xxd` implementation does not support upstream's two-argument output form.
- Loaded Conan `conanbuild.sh` for `xsltproc` and `conanrun.sh` for runtime library paths.
- Signed build-tree ELF files before CTest; 16 ELF files were signed, including `morpheus`, `libModelTesting.so`, and all 10 GTest executables.
- CTest must be run from `work/morpheus-build/morpheus`; the top-level build directory has no `CTestTestfile.cmake` and reports zero tests.

## Evidence

- Build/sign run_dir: `/storage/Users/currentUser/ohos-test-runs/codex-a-morpheus-upstream-gtest-r4-20260802-151701-21745`
- Effective CTest run_dir: `/storage/Users/currentUser/ohos-test-runs/codex-a-morpheus-upstream-gtest-r5-ctest-subdir-20260802-154259-31246`
- CTest list: `r5/artifacts/ctest-list.txt`
- CTest log: `r5/artifacts/ctest.log`
- JUnit XML: `r5/artifacts/ctest-junit.xml`

## Result

`ctest --test-dir .../work/morpheus-build/morpheus --output-on-failure --timeout 300 -j1 --output-junit ...`

- Result: `57/57` CTest entries passed.
- Exit code: `0`.
- Total test time: `107.71 sec`.
- JUnit testcase count: `57`.

Label summary from CTest:

- `Component`: 6 tests
- `Interaction`: 5 tests
- `Motility`: 1 test
- `Core`: 50 tests
- `CPM`: 2 tests
- `Models`: 1 test

## Count Reconciliation

A raw grep of `TEST(...)` in `morpheus/testing` sees 59 macro occurrences, but that is not the executable test count:

- `VDOUBLE.IDX_OPERATOR` is guarded by `#ifdef HAVE_VEC_INDEX_OPRT` and was not compiled/registered.
- One old `System.Solver_RK4` occurrence is inside a block comment.

The authoritative executed count for this OHOS run is the GTest/CTest registered count: `57`.

## Examples

Official example XML models were identified separately, but were not part of this GTest run. They are not registered as CTest tests upstream. The release source contains 43 example XML files; 36 use `Gnuplotter`, 8 use `TiffPlotter`, 39 use `ModelGraph`, 28 use `Logger`, and 4 use `HistogramLogger`. The current package is CLI-only, the OHOS device has no `gnuplot`, and the recipe configures `MORPHEUS_GRAPHVIZ=None`. Examples therefore need a separate runner that splits core simulation checks from TIFF/plot/model-graph output checks, and should not be counted in the GTest result.
