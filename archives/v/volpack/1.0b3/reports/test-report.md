# VolPack 1.0b3 native HarmonyOS PC test report

Date: 2026-09-28. Target: HarmonyOS aarch64, Clang 15, Conan 2.29.1.

## Source and dependency checks

- Task #11740 assigned to `2501_91199785` at test time.
- No third-party library dependencies for the core VolPack package; the Tcl/Tk
  `vprender` demonstration is a separate distribution and is not packaged.
- Stanford `.tar.Z` SHA256:
  `d7cfd5f6819cccf88363d2270377e547a07f35da6a0dac45845ecc1640e410fa`.
- Debian versioned `.orig.tar.gz` SHA256:
  `dce3d892ad34b2810fc80b0592c7224a4606f8ebfb8206421e24288753f230d7`.
  The `vp_*.c` implementations, `volpack.h`, MRI data and reference PPM match
  the Stanford release byte-for-byte; Debian repacks the build-system files.

## Native build and upstream test inventory

`conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`
completed successfully from a clean cached source. The target's external
Debian connection was unavailable, so only this *local validation* used
`VOLPACK_SOURCE_ARCHIVE` pointing at the SHA256-verified Debian archive;
the submitted `conandata.yml` retains the canonical Debian URL.

The distributed `make check` target has zero executable cases. The source
instead supplies `examples/test.csh`; the recipe runs its four rendering modes
with a portable `sh` harness and checks each output against upstream
`examples/check.ppm` using `cmp`:

| Rendering path | Result |
| --- | --- |
| Raw volume | PASS, byte-identical |
| Octree volume | PASS, byte-identical |
| Classified volume | PASS, byte-identical |
| Classified volume with octree | PASS, byte-identical |

Upstream functional tests: **4/4 PASS**. No upstream test source was changed.

## Packaged consumer and CI simulation

The standalone C consumer links the Conan package, creates a `vpContext`,
sets a 2×3×4 volume, reads back X/Y/Z through `vpGeti`, and destroys the
context: **5/5 assertions PASS**. The CI negative test temporarily hid both
`lib/` and `include/`; the consumer failed as expected, confirming it really
uses the packaged artifact.

Target-local `CI_PACKAGES=archives/v/volpack/1.0b3 zsh
ci/conan/build_and_test.sh` passed on 2026-09-28:

| Gate | Result |
| --- | --- |
| L0 | PASS |
| L1 | PASS (upstream and consumer tests) |
| L2 | SKIP (library has no bin directory) |
| L4 | PASS (patch scan) |
| L5 | PASS (library artifact present) |

CI simulation summary: **1/1 package PASS**. This is local evidence, not a
claim that the hosted PR CI has run or that the package has been published.

## CI #63564 correction and target-local rerun

Hosted PR CI #63564 failed before compilation: its HMDFS-backed Conan build
folder made Autoconf's mode-0700 `confXXXXXX` directory unwritable to
`config.status`. The recipe now applies a guarded OHOS-only group-writable
temporary-directory substitution before running configure.

The corrected recipe passed a fresh target-local run of the same
`ci/conan/build_and_test.sh` pipeline on 2026-09-28. `config.status` created
every Makefile and `config.h`; the four upstream rendering paths again matched
`check.ppm` (4/4), and the packaged consumer passed. L0, L1, L4 and L5 passed;
L2 was skipped because this is a library. Summary: **1/1 package PASS**.
The target-local log is
`/data/storage/el2/base/files/volpack-1.0b3-ci-fix-20260928T1400/w3.log`,
SHA256 `f6ab675f224f920590eebea425328da8b45cffdc6e066722974d1fb52ccf41c8`.
This is not a claim that the hosted CI rerun has passed.
