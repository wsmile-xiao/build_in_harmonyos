# libmatio 1.5.30 verification report

## Environment

- HarmonyOS PC aarch64 real device (HongMeng Kernel 1.12.0)
- Clang 15 (OHOS device toolchain)
- Conan 2.29.1

## Upstream tests (in conan create build phase)

CMake route: `test/tests/*.at` (3338 AT_SETUP cases, 5389 AT_CHECK assertions)
converted by `test/convert_at_to_ctest.py` into ctest entries, same coverage as
autotools `make check`.

- Upstream test cases (AT_SETUP): 3338
- Upstream in-case assertions (AT_CHECK): 5389
- CTest entries emitted by the converter: 8197 — passed 8197 / failed 0 / skipped 0
- Evidence: `100% tests passed, 0 tests failed out of 8197` (matio-create12.log,
  full ordered run inside `conan create`; the 8197 counts CTest entries,
  not test cases)

Note on methodology: chained tests (`_1` → `_N`, e.g. copy → delete → whos
compare) have order dependencies; running them in split `ctest -I` ranges
breaks the chain and produces spurious failures. The authoritative number comes
from a complete ordered run.

How the three numbers relate (they are counts of different things, and are NOT
meant to add up): 3338 is the number of autotest *cases* (`AT_SETUP` blocks in
`test/tests/*.at`); 5389 is the number of `AT_CHECK` *assertions* inside those
cases; 8197 is the number of *CTest entries* the converter
(`test/convert_at_to_ctest.py`) emits — it splits each case into its chained
steps (`_1`..`_N`, one CTest entry each) and folds each step's `AT_CHECK`s into
that entry. So 3338+5389=8727 ≠ 8197 by construction; the correct reading is:
3338 cases / 5389 in-case assertions / 8197 executable CTest entries, all from
the same upstream test suite. Total test cases after adaptation: 3339
(3338 upstream AT_SETUP cases + 1 test_package test case).

## test_package

Programmatically generated MAT data, consumed via public API from the final
installed package (CMakeDeps). Suites:

| Suite | Coverage |
|-------|----------|
| verify_roundtrip × 5 | MAT v4, v5 uncompressed, v5 compressed, v7.3 uncompressed, v7.3 compressed — create/write/read/variable name/class type/dims/values roundtrip each |
| verify_error_inputs | error inputs: NULL/invalid handles, missing variable read, double close |
| verify_long_tmpdir_delete | regression for upstream mktemp buffer defect: writable TMPDIR longer than legacy 21-byte MAT_MKTEMP_BUF_SIZE; create → write 2 vars → delete 1 → reopen; asserts delete rc=0, deleted var gone, survivor data intact |

- Test binaries (test cases): 1 (test_libmatio — this is the +1 case in the
  3339 adapted total)
- Test groups (suites in code): 3 (verify_roundtrip, verify_error_inputs, verify_long_tmpdir_delete)
- Roundtrip invocations: 5 (MAT v4, v5 uncompressed, v5 compressed, v7.3 uncompressed, v7.3 compressed)
- Runtime assertions: 100
  - roundtrip 5 × 16 = 80 (14 CHECK + 2 bit-pattern data comparisons each)
  - error inputs 6
  - long-TMPDIR regression 14 (13 CHECK + 1 memcmp; includes dir-length > 21 precondition)
- Passed: 100
- Failed: 0
- Skipped: 0
- Evidence: `test_package: 100 checks, 0 failures` (fresh `conan test` run, 2026-09-04)

MAT v4/v5/compressed/v7.3 features counted above were all actually built
(MATIO_WITH_HDF5=ON, MATIO_WITH_ZLIB=ON) and verified.

## ELF verification

- `libmatio.so.1.5.30`: ELF shared object, 64-bit LSB arm64
- `matdump`: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)

Both executed on-device: `test_libmatio` exit 0, `matdump` runs and prints usage.

## Patches

- 0001-hdf5-conan2-cmakedeps-target.patch (conan): link flat CMakeDeps
  `hdf5::hdf5` INTERFACE target (upstream cascade only knows
  hdf5::hdf5-shared/-static and FindHDF5's HDF5::HDF5)
- 0002-mktemp-tmpdir-env.patch (portability): TMPDIR-first temp dir resolution +
  PATH_MAX-sized template buffers (upstream hardcodes /tmp with 21-byte buffer;
  OHOS /tmp is read-only and long TMPDIRs were rejected by the snprintf length
  check — 391/8197 CTest entries failed before, 0 after)

Both apply cleanly with `patch -p1 --dry-run` to a fresh unpacked tarball.

## Result

Recipe verified on a HarmonyOS PC aarch64 device; eligible for built status.

## Scoped CI run (ci/conan/build_and_test.sh, 2026-09-04)

`zsh ci/conan/build_and_test.sh archives/l/libmatio/1.5.30`
(CONAN_PROFILE=ohos-aarch64-device, JUNK_PR_DIFF simulating the 15-file PR):

- G0_RESULT=pass (knowledge graph integrity, 540 entries)
- JC_RESULT=pass (junk files, PR-diff mode: single package libmatio)
- L0_RESULT=pass (quality gates incl. R36 dependency registry, R37 version
  collision, R39 directory structure)
- L1_RESULT=pass (test_package executed; upstream ctest evidence in build log)
- L2_RESULT=skip (non-blocking platform smoke rule: matdump links shared
  libmatio.so.14 via absolute DT_NEEDED without RUNPATH; on this OHOS device
  running matdump without LD_LIBRARY_PATH failed to load libmatio.so.14, and
  setting LD_LIBRARY_PATH to the package lib dir made it run. Same skip class
  as abduco/0.6. Manual on-device smoke: `matdump --version` →
  `matdump 1.5.30` exit 0, `matdump -d file.mat` prints correct variable
  values with LD_LIBRARY_PATH set)
- L4_RESULT=pass (patches clean)
- L5_RESULT=pass (bin/ + lib/ content; no system-lib collision; DT_SONAME ok)
- Upstream ctest inside CI: `100% tests passed, 0 tests failed out of 8197`,
  Total Test time 628.79 sec
- Build Summary: Total 1, Success 1, Failed 0, Pass rate 100.0%

CI pre-download step rewrote conandata.yml URLs to file:// during the run; the
post-run restore was verified and the final conandata.yml in the archive tree
contains only the official GitHub release URL (a fresh `conan create` from that
URL was re-run afterwards: exit 0, 100 checks 0 failures).
