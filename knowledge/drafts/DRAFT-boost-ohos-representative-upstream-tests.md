# DRAFT: Boost OHOS Component Upstream Test Inventory

> Status: Draft | Updated: 2026-08-27
> Source events: `boost/1.90.0.2.1` PR review comments `186766151`, `186800536`
> Task hall: `4415`
> PR: https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/6712

## Summary

Boost packaging PRs must not report upstream tests as zero or replace them with
a tiny smoke subset. Boost release archives carry a large `libs/*/test` tree
even when the Conan recipe publishes only selected components. Review can fail
both under-reporting and very low representative coverage.

## Trigger

The first review failed when the PR body declared upstream tests as N/A. The
follow-up review failed again after only 4 representative checks were added:
3 C++ quick tests plus one Boost.Python ELF check were treated as too small for
the selected component inventory.

## Adaptation Pattern

For a selected Boost component package, keep three numbers separate:

- full upstream test-tree scale
- selected component test-tree scale
- selected component evidence actually built, executed, or statically verified

For `boost/1.90.0.2.1`, the CMake release source contains 16590 test-related
files under `libs/*/test` by the PR counting policy (`*.cpp`, `*.hpp`, `*.h`,
`*.py`, `Jamfile*`, and `CMakeLists.txt`). The selected component trees contain
380 files:

- `filesystem`: 53
- `program_options`: 22
- `system`: 118
- `python`: 187

The recipe now gathers 356 selected-component evidence items during `build()`:

- 171 CTest entries from Boost.System and Boost.ProgramOptions using a second
  CMake build tree with `BUILD_TESTING=ON`
- 2 additional CMake compile/link-only checks
- 4 Boost.System `error_code_test` CTest entries explicitly skipped for OHOS
  libc error message/category semantic differences
- 15 Boost.Filesystem Jamfile-derived build checks compiled from upstream
  sources, with 14 runtime tests on OHOS because the 1.90.0 CMake source has
  no filesystem `test/CMakeLists.txt`; `operations_unit_v4` is compile-only
  because its upstream query test inspects `/` and HNP users receive
  `Permission denied`
- 89 Boost.Python top-level `.cpp` compile checks, skipping only documented
  upstream negative, Windows-only, or `std::auto_ptr` conditional entries;
  `copy_ctor_mutates_rhs.cpp` is kept by force-including `boost/mpl/bool.hpp`
  for the standalone private-header compile context, while `pointee.cpp` is
  skipped because it directly names removed `std::auto_ptr`
- 72 Boost.Python `.py` script `py_compile` checks with `PYTHONPYCACHEPREFIX`
  redirected into the build tree
- 7 Boost.Python extension modules built and verified for ELF magic,
  `.codesign`, `PyInit_*_ext`, and `NEEDED` metadata

## OHOS Notes

On OHOS, upstream tests consume build-tree artifacts before `package()` can sign
installed libraries. The recipe must sign test executables, extension modules,
and build-tree shared libraries before running CTest or direct runtime tests.
Only loadable ELF files (`ET_EXEC`/`ET_DYN`) should be signed; relocatable `.o`
compile-check outputs must be left alone.

Boost.Python has an extra HNP limitation. Official CI showed that HNP Python
under `/data/service/hnp` rejects user-path extension modules from the Conan
cache with `Permission denied` even after self-signing. Treat those live-import
tests as E212-limited: keep C++ compilation, Python script syntax checks, and
extension ELF/ABI metadata verification, but do not count live imports as
runtime passes under HNP Python.

## Validation

Run the OHOS package CI:

```sh
CI_PACKAGES="archives/b/boost/1.90.0.2.1" CI_BRANCH="feat/boost-1.90.0.2.1" CI_PR_NUMBER="6712" zsh ci/conan/build_and_test.sh
```

Expected evidence in the Conan build log:

```text
Configuring Boost upstream CMake tests for system/program_options
Building 171 Boost upstream CMake test targets
ctest -R ^(run|run-fail|compile-fail|link-fail)-boost_(system|program_options)- -E ^run-boost_system-error_code_test
Building Boost.Filesystem upstream tests from Jamfile inventory: 15 build checks, 14 runtime tests
Skipping Boost.Filesystem runtime check boost_filesystem_operations_unit_v4
PASS: Boost.Python upstream C++ compile checks 89/89
PASS: Boost.Python upstream Python script py_compile checks 72/72
E212: HNP Python cannot dlopen user-path Boost.Python test modules
PASS: Boost.Python upstream module ELF, .codesign, PyInit, and NEEDED metadata verified
Boost upstream component tests summary: ... total evidence 356
```

## Do Not

- Do not claim Boost upstream test count is zero when the release contains
  `libs/*/test`.
- Do not use `test_package` alone as upstream test evidence.
- Do not present a tiny quick-test subset as enough coverage for a large
  selected Boost component inventory.
- Do not count HNP Python user-path extension imports as runtime passes when
  they are only ELF/ABI metadata checks.
