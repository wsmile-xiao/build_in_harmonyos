# BLAS 3.12.0 HarmonyOS PC adaptation notes

## W0 dependency audit

- Upstream source: Netlib `blas-3.12.0.tgz`.
- Source SHA256: `ccc41b5d088e50db0030317ae9b0c9af375710c1392acad1fe209602da5a5aad`.
- Runtime and build dependency count: one tool requirement.
- Dependency: `flang-ohos/20.1.0`, which supplies the native OHOS Fortran compiler and
  the FortranRuntime/FortranDecimal static runtime archives.
- No external BLAS, CMake package, C library, or test framework dependency is needed.
- No dependency split is required for this library.

## W1 source and build analysis

The official archive is a standalone `BLAS-3.12.0` tree. It contains:

- 163 real Fortran source files, including fixed-form `.f` and free-form `.f90`
  routines. The tarball also contains 163 macOS `._` metadata entries, which
  are ignored by the build.
- A CMake build that produces `libblas.a` by default.
- A legacy Makefile and `make.inc`.
- The archive has a top-level macOS `._BLAS-3.12.0` entry beside the real
  `BLAS-3.12.0/` source root. The recipe preserves this layout with
  `strip_root=False`, points CMake at `BLAS-3.12.0`, and uses
  `no_copy_source=True` to avoid a second full source tree on the device.
- The official `TESTING/` tree with 12 drivers: three levels for each of
  single, double, complex, and complex16 precision.

The library has no public C/C++ headers. The consumer ABI is the conventional
Fortran symbol interface with trailing underscores. The package therefore exposes
the static library and the required Flang runtime archives rather than inventing
a C header layer.

## W2 Conan recipe

The recipe uses the official Netlib archive directly from `source()`, with a fixed
SHA256. `conandata.yml` is intentionally absent so the known CI pre-download path
cannot trigger the uninitialized `BUILD_DIR` problem described in the common guide.

The native OHOS build is static and uses:

```text
flang-ohos/20.1.0
CMAKE_Fortran_COMPILER=<flang package>/bin/flang
CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY
--target=aarch64-linux-ohos
--sysroot=<OHOS SDK>/sysroot
-resource-dir=<OHOS SDK>/llvm/lib/clang/15.0.4
```

The build environment puts the OHOS SDK LLVM directory before the Flang package
library directory in `LD_LIBRARY_PATH`. This keeps the linker runtime separate
from the Flang runtime, following the existing OpenBLAS and LAPACK recipes.

The upstream standalone `blas.pc.in` refers to `LAPACK_VERSION`, so the recipe
sets `-DLAPACK_VERSION=3.12.0` to keep the installed pkg-config metadata
versioned.

`package()` installs the upstream CMake result, the package license notice, and
the two Flang runtime archives required by static consumers. `package_info()`
exports `blas`, `FortranRuntime`, and `FortranDecimal` in that order.

## W3 consumer test

`test_package` uses a CMake consumer and directly calls six public Fortran BLAS
entry points:

| Routine | Check |
|---|---|
| `ddot_` | double precision dot product |
| `dgemm_` | 2x2 matrix multiplication |
| `dgemv_` | matrix-vector multiplication |
| `dnrm2_` | Euclidean norm |
| `dscal_` | vector scaling |
| `lsame_` | case-insensitive character comparison |

The consumer executable is signed with `binary-sign-tool` before native OHOS
execution. Cross builds still verify that the executable was produced.

## W4 local preflight

The source archive hash has been verified locally. Both Conan recipe files pass
Python 3.12.10 compilation, both YAML files parse successfully, the consumer
source passes the DevEco OHOS clang check with `-Wall -Wextra -Werror`, and
`git diff --check` plus the directory-boundary check pass.

The current Windows host does not have `conan` or `cmake` on `PATH`, and the
DevEco OHOS SDK has no Flang compiler, so a local `conan create` cannot run in
this round.

The upstream Fortran test executables are deliberately not enabled in the recipe
build. The current `flang-ohos` package is a minimal compiler/runtime package and
does not provide the CRT set needed to link these native Fortran test programs.
The 12 upstream tests remain declared as `not_run`, not as passed or silently
removed. The C consumer test is the feasible packaged-consumer validation path.

## W5 native shadow CI

Prepare an isolated job on an idle device:

```sh
sh "$HOME/bin/ohos-prepare-isolated-conan-job.sh" \
  --user codex \
  --job blas-3.12.0-<timestamp> \
  --package archives/b/blas/3.12.0 \
  --repo-source "$HOME/ohos-users/codex/<existing-job>/repo/build_in_harmonyos"
sh "$HOME/ohos-users/codex/blas-3.12.0-<timestamp>/run-conan-heavy.sh"
```

Then run the Conan command supplied by the job:

```sh
conan create archives/b/blas/3.12.0 \
  --name blas --version 3.12.0 \
  -pr:h ohos-native -pr:b ohos-native --build=missing
```

Record the runner exit code, upstream `TESTING` result, six consumer assertions,
package file list, and ELF/symbol inspection. Do not put device addresses,
credentials, or raw runner paths into this directory.

Observed shadow results for this round:

- Attempt 1 reached L0 and failed in `source()` because `strip_root=True`
  rejected the archive's top-level `._BLAS-3.12.0` entry. The recipe was
  corrected to preserve the archive layout and select `BLAS-3.12.0`.
- Attempt 2 reached L0 and passed source extraction, but Conan failed while
  copying the source tree into the build folder with `ENOSPC`; CMake and
  Fortran compilation did not start.
- Attempt 3 failed before the Conan setup could write its temporary directory
  with the same device storage quota error.
- A retry using the device's alternate data path could not create a new
  runner directory; the device rejected new writes with `ENOSPC` there too.
- Attempt 5 reached Flang download and source extraction, then exposed the
  Conan 2.29.1 CMake helper API: `CMake.configure()` uses
  `build_script_folder`, not `source_folder`.
- Attempt 6 reached the Flang dependency but hit `ENOSPC` while extracting the
  88 MB tool package. After cleaning only this job's caches, the next run
  installed Flang successfully.
- Attempt 7 reached CMake and exposed the upstream legacy
  `cmake_minimum_required()` incompatibility with CMake 4.1. The recipe now
  supplies `CMAKE_POLICY_VERSION_MINIMUM=3.5`.
- Attempt 8 passed CMake policy handling and Fortran compiler detection, then
  showed that OHOS Flang 20.1.0 rejects GCC's `-frecursive` flag. The flag was
  removed from the recipe.
- Attempts 9 and 10 confirmed the remaining `/storage` quota boundary: CMake
  and compilation started, but the job ran out of space during generator
  creation or at roughly 59% of the Fortran objects.
- Attempt 11 reused an existing device Flang cache. The complete BLAS static
  library built and was packaged; the first consumer run found a test mistake
  in the column-major `dgemm` expectation (5/6 passed).
- Attempt 12 reran only `test_package` with the corrected expectation and
  passed all 6 assertions after signing and executing the consumer.
- A package rebuild then exposed that `LICENSE` was not exported into the
  Conan recipe. Adding `exports = "LICENSE"` fixed the package layout.
- Attempt 15 rebuilt the package with `licenses/LICENSE` present and again
  passed all 6 signed consumer assertions. The formal full-pipeline rerun
  could not start its runner logs after the device quota filled again.
- Attempt 17 reran the complete single-package `ci/conan/build_and_test.sh`
  pipeline with the existing Flang cache. L0, L1, L4, and L5 passed; L2 was
  correctly skipped because this static-only package has no `bin/` directory.
  The runner reported `Total: 1`, `Success: 1`, `Failed: 0`, and a 100% pass
  rate. The signed `test_package` consumer passed all 6 assertions.

## Current status

Status: formal single-package shadow CI passed. The package build, signed
consumer, L0, L1, L4, and L5 checks passed; L2 was skipped because the package
has no `bin/` directory.

- Worktree and branch are isolated for `blas/3.12.0`.
- W0 dependency audit, W1 source analysis, W2 recipe, and W3 consumer test are
  prepared.
- Source SHA256 is verified.
- Native L0 passed. Conan built all four precision families into `libblas.a`,
  packaged the Flang runtime archives, `blas.pc`, and `licenses/LICENSE`.
- The signed `test_package` consumer passed `ddot`, `dgemm`, `dgemv`, `dnrm2`,
  `dscal`, and `lsame` (6/6).
- Read-only artifact inspection found 151 archive members and the six expected
  public Fortran symbols.
- The formal single-package runner reported 1/1 success with a 100% pass rate;
  L4 found no patches, L5 found content under `lib/`, and L2 was skipped by
  the package shape because there is no `bin/` directory.
- The 12 upstream Fortran executables remain not run. The recipe intentionally
  keeps `BUILD_TESTING=OFF`; the upstream test programs are not linkable with
  the current minimal Flang runtime set.
