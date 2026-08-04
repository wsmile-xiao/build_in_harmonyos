# libxc 7.1.2 adaptation notes

## Scope

- Build static `libxc.a` and `libxcf03.a`.
- Install the C headers and the two Fortran module files.
- Enable `MAXORDER=3` for KXC consumers.
- Disable the Python binding in the package; the upstream Python suite is
  executed separately against the same official source and built library.
- Remove `bin/xc-info` from the package, so this remains a library package and
  does not require `commands.json`.

## Floating-point reproducibility

The package backports only the CMake `-ffp-contract=off` behavior from official
upstream commit `ecdc2080abed217b4ac2e0bdaf3ac530995d9754`. That commit directly
follows the 7.1.2 tag, so the release does not contain the fix. The upstream CI
canary and Autotools changes are not part of this CMake-only recipe. The patch
was regenerated from pristine and modified 7.1.2 inputs with the unchanged
`refresh-patch --auto` tool on HarmonyOS; its SHA-256 is
`12CCEA6F8B049F95283C94D87049828F2712C0FCB3A47236D309DE1F78A0C9E1`.
Replaying it produces CMakeLists.txt blob
`87926b40c044147a37678e7e6e1a851a67a03054`, exactly matching the file in the
official upstream fix commit. The flag is needed because FMA contraction
changes several full-precision functional references on FMA-capable processors.

## Validation contract

The 7.1.2 official archive, upstream test inventory, CMake registration, C and
Fortran consumers, archive contents, and AArch64 object format must be measured
again. The 7.1.0 results below are migration evidence only and do not satisfy
any 7.1.2 acceptance gate.

## LibXC 7.1.2 host upstream validation

The official 7.1.2 source was configured as a Windows shared build with
`BUILD_TESTING=ON`, `ENABLE_FORTRAN=OFF`, `ENABLE_PYTHON=OFF`, and
`MAXORDER=3`. The build reached 349/349 Ninja edges with one build job. CTest
registered 23 entries: 20 `python-*` wrappers and three native entries. The
native command is therefore `ctest -E '^python-' --output-on-failure -j1`, not
the historical `'^python-tests$'` expression. All three native entries passed.

Pytest collected 14,084 unique nodeids. The full run returned RC 0 with
`PASS=13987`, `SKIP=79`, `XFAIL=18`, and zero FAIL, ERROR, XPASS, TIMEOUT, or
NOT_RUN terminals. Together with the three native entries, the 7.1.2 official
inventory contains 14,087 independent validation entries. Its aggregate
expected-terminal accounting is `PASS=13990`, `SKIP=79`, `XFAIL=18`.

The first direct pytest collection returned RC 2 with 1,414 import errors. On
Windows, `ctypes.util.find_library("xc")` did not resolve the already built
`libxc.dll`; this was a test-loader layout failure, not a source test failure,
and is excluded from acceptance counts. Copying the identical DLL only inside
the isolated validation tree to `src/pylibxc/libxc.dll` made collection and the
full run succeed. The staged and built DLL SHA-256 values matched exactly.

The corrected collection log SHA-256 is
`4EA64DBFF482CC55B48BC14701D2B898875F8C004EEB5E608F8CD191912FA615`;
the full pytest stdout SHA-256 is
`BADEDAD9947E445F3CA10B67B66AD6CCCD8B89A750420E7EA4EF48AAED4F3563`.
The complete evidence is recorded in `reports/test-report.md`. This host result
is supplementary to the HarmonyOS target upstream result below.

## LibXC 7.1.2 HarmonyOS PC target upstream validation

The accepted r10 run used the official 7.1.2 source, the exact candidate patch,
and PR candidate commit `09d4883981167bca6fc35e3f8a228a3c26e44eb3` on an
authorized HarmonyOS PC aarch64 device. The runner used one Ninja build job,
serial pytest execution, and validated a frozen
15-file input closure before extracting or building. The shared build completed
349/349 Ninja edges and all three non-Python CTest entries passed.

The target collected and executed the same 14,084 unique pytest nodeids with
`PASS=13987`, `SKIP=79`, `XFAIL=18`, and zero FAIL, ERROR, XPASS, TIMEOUT, or
NOT_RUN terminals. The combined official inventory therefore has 14,087
entries and expected-terminal accounting `PASS=13990`, `SKIP=79`,
`XFAIL=18`. The full pytest execution took 972.49 seconds.

Two fail-closed diagnostics changed only the runner dependency/layout closure.
Missing SymPy and mpmath allowed pytest to exit zero while collecting only
13,966 nodeids because upstream uses `pytest.importorskip`; the final run pins
both offline wheels and asserts the exact 14,084-nodeid inventory. With those
dependencies present, r7 reached all 14,084 terminals but pytest's default
temporary-root ownership check rejected an HMDFS directory exposed as UID
`20001006` while the process ran as UID `20020107`. The exact failing test
passed with an explicit base directory, and r10 used separate
`--basetemp` paths for collection and full execution.

The atomically published result contains 35 hash-bound evidence files. Its
downloaded tar SHA-256 is
`18EDFFB1D980F33DC802F88CA9EF9ECFD6139EB365C980C2001A53C62C4D95ED`,
and the independent result validator returned PASS at
`E:/HarmonyPC/validation/libxc-7.1.2-target-upstream-r10-20260801/downloaded/result`.

## LibXC 7.1.2 HarmonyOS PC target package validation

A fresh run on an authorized HarmonyOS PC aarch64 device used one build job and
candidate index tree `d47baa00c4def998fb5d88e438a62df4a7b923c1`. The candidate
archive SHA-256 was
`A32061DA4CEA263897D81D112B09B97154BA406B8AE611F115E60EB75F57052D`.
The target-side candidate validator reported `CR=0` and exact file-list
agreement before the build.

`conan create` returned zero and produced the complete local package reference
`libxc/7.1.2#388674bd8ae779d9c327a304f5182081:67b1ef552f88cbbdfea884e9d0a9077b41cdad94#9d58b49573531ab0d22e03149e2f2d6e`.
Both independent package consumer flows compiled, linked, and executed on the
target: C `PASS=1/1` and LLVMFlang Fortran KXC `PASS=1/1`. Aggregate consumer
accounting is `PASS=2`, with `SKIP=0`, `XFAIL=0`, `FAIL=0`, `ERROR=0`,
`XPASS=0`, `TIMEOUT=0`, and `NOT_RUN=0`; the 11 internal assertions are not
counted as tests.

The installed package contains static `libxc.a` and `libxcf03.a`, both required
Fortran module files, and `lib/cmake/Libxc/libxc-fortran-abi.cmake`. Every one
of the 328 inspected objects from `libxc.a` and the Fortran object from
`libxcf03.a` is ELF64 little-endian AArch64. The downloaded result independently
validated all 39 hash-bound evidence files. Its local evidence directory is
`E:/HarmonyPC/validation/libxc-7.1.2-target-r5-20260731/downloaded/result`.

## Historical 7.1.0 validation evidence

The complete official source test inventory is 13,807 independent entries:
three CTest entries plus 13,804 uniquely collected pytest nodeids. A successful
candidate must have zero FAIL, ERROR, XPASS, TIMEOUT, or NOT_RUN terminals. The
two package consumers are counted separately as two flows, not as assertions.

The full pytest command clears the upstream default marker filter:
'python -m pytest -o addopts= testsuite'. The 13,804 expected nodeids are
frozen and hash-bound before the external target run; the recipe itself keeps
'BUILD_TESTING=OFF' so 'conan create' does not silently claim this external
upstream suite.

The shared upstream build registers one `python-tests` CTest wrapper in
addition to the three native entries. The official command therefore excludes
that wrapper before invoking pytest separately:
`ctest -E '^python-tests$' --output-on-failure`. This prevents the 13,804
pytest nodeids from being executed and counted twice.

Host-only preflight on 2026-07-29 used CMake 4.4.0, Ninja 1.13.2, GCC 16.1.0,
Python 3.13.7, pytest 8.4.2, a shared C library, `ENABLE_FORTRAN=OFF`, and
`MAXORDER=3`. The three native CTest entries passed 3/3. Pytest collection
returned 13,804 nodeids, all 13,804 unique, with zero collection errors; the
collection stdout SHA-256 is
`C63A6772D647C0AFE04CDC20CB5C2FB091765460731A0233076E5BDD81841F5B`.
The full pytest execution completed in 336.36 seconds with `PASS=13707`,
`SKIP=79`, `XFAIL=18`, `FAIL=0`, `ERROR=0`, `XPASS=0`, `TIMEOUT=0`, and
`NOT_RUN=0`. Its stdout SHA-256 is
`2DF86122A36C5F8661382F980943279241CFE43951838F08FB24D89B8B212351`;
stderr was empty. The 79 skips and 18 expected failures retain their upstream
terminal classes and are not counted as passes. Across the complete official
inventory, the host result is therefore `PASS=13710`, `SKIP=79`, `XFAIL=18`,
and all unexpected terminal classes zero out of 13,807 entries.

The C package consumer was also compiled with GCC 16.1.0 using
`-Wall -Wextra -Werror` and ran successfully; its executable SHA-256 is
`5EA59AEBE8213C4051AD2EE9A8ECE7D5FCB4424E6BCF60F3CD8DAFDFC95AB8BF`.
The available `flang-ohos/20.1.0` executable is an aarch64 ELF and cannot run
on the Windows host, so the host-only substantive Fortran package consumer is
`NOT_RUN`. The target result below closes that platform-specific gap; the host
upstream suite remains supplementary evidence rather than a substitute for W3.

## Historical 7.1.0 HarmonyOS PC W3

A fresh run on an authorized HarmonyOS PC aarch64 device used candidate index
tree `7a0da5b557e71910f15524fed2712e920e34f535`, based on
`origin/main=a73ac478cc4cdec4eefff577711d567fbbcc9eae`. The frozen input exported
Git index blobs with `core.autocrlf=false`; the floating-point patch SHA-256
was `8EEE961B855B82D7ADC0B2A48B68739295E134EA7095A6B2DA412D624D47B495`.

The target environment used Conan 2.29.1, CMake 4.1.2, Ninja 1.13.1, Clang
15.0.4, the `ohos-aarch64` profile, and the published
`flang-ohos/20.1.0#ef1e4e5bb35d3d6055bdc9ed6b26479c` recipe. `conan create`
returned zero and produced the exact local package reference
`libxc/7.1.0#675879e2931918f51ba45a4c80e586aa:67b1ef552f88cbbdfea884e9d0a9077b41cdad94#8ea060c52ef72e4bd2702415eb5eaef1`.

Both independent package consumer flows compiled, linked, and ran on the
target: C `PASS=1/1` and Fortran KXC `PASS=1/1`. Aggregate consumer accounting
is therefore `PASS=2`, with `SKIP=0`, `XFAIL=0`, `FAIL=0`, `ERROR=0`,
`XPASS=0`, `TIMEOUT=0`, and `NOT_RUN=0`. The 11 internal assertions are not
counted as tests. An object extracted from `lib/libxc.a` was ELF64 little-endian
`Machine: AArch64`; the package contained `libxc.a`, `libxcf03.a`, and both
required LLVMFlang module files, with no shared library or `bin/` directory.

The atomically published result contains 26 hash-bound evidence files. The
downloaded bundle is
`E:/HarmonyPC/validation/libxc-7.1.0-target-r2-20260729/downloaded/result-bundle.tar.gz`
with SHA-256
`B1762C5818D27EAEC033473005C942EF7DAB0705403A1F1D99CE1E9D953EA143`.
The independent validator passed both on the device and after download.

An earlier fresh r1 run also completed `conan create` and both consumers, but
its evidence parser incorrectly required package revisions in the default
`conan list` JSON. It was retained as `result.incomplete` and is not used for
acceptance. The r2 run used a new device path and a fresh Conan home; its
package revision was instead bound across `conan list`, `conan graph info`,
and the successful create log.

The floating-point patch is a preventive upstream backport, not a new local
failure pattern, so this adaptation does not add a knowledge draft for it.

## Fortran ABI

The installed `.mod` files are compiler-specific. The Flang tool requirement
uses Conan `full_mode` package identity. Downstream recipes using
`Libxc::xcf03` must declare `flang-ohos/20.1.0`, use CMake 3.24 or newer, enable
the Fortran language, and then call `find_package(Libxc COMPONENTS Fortran)`.
The exported module rejects other compiler IDs or versions and makes direct
use of the Fortran target without the explicit component contract fail closed;
C-only consumers are not constrained by the Fortran ABI.

A host-only CMake logic matrix exercised the exported ABI module directly.
The C-only and exact `LLVMFlang 20.1.0` cases configured successfully; missing
the explicit component, leaving the Fortran language disabled, using compiler
ID `GNU`, and using `LLVMFlang 19.1.0` each failed as required. This validates
the fail-closed configuration logic. The fresh W3 result separately compiled,
linked, and executed the substantive OHOS LLVMFlang 20.1.0 consumer.
