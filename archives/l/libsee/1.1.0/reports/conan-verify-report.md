# Conan Verify Report — libsee 1.1.0

**Verdict**: PASS (W3 plus independent W4 artifact/security/baseline checks)
**Reference**: `libsee/1.1.0@ohpcd/stable`
**Profile**: ohos-aarch64
**Date**: 2026-09-04

## G0: ✅ PASS
  📦 构建系统: cmake
  ✅ CMake uses the Linux-compatible OHOS mode (`CMAKE_SYSTEM_NAME=Linux`, `CMAKE_SYSTEM_PROCESSOR=aarch64`).

## G1: ✅ PASS
  ✅ Conan recipe declares source, build, package, package_info and the `test_package`.
  ✅ `conandata.yml` declares the portability patch and `strip: 1` for its `a/libsee.c`/`b/libsee.c` paths.

## G2: ✅ PASS
  ✅ Exact OHOS `conan create` completed with exit 0; CMake built `libsee.so` and the five consumer/preload assertions passed.
  📄 证据: `conan-cpp17-summary.md`

## G3: ✅ PASS
  ✅ No system-library name collision was detected for this diagnostic library.

## G4: ✅ PASS
  The final package reference was `libsee/1.1.0#64c9f79726dab69089aaf98568fe9fb1:01d92cf349a0dd98ff915f4bd99a04430171517f#a560b789e77385e524d5707702efc49b`.
  `conan cache path` resolved `/storage/Users/currentUser/.conan2/p/b/libsef0826f2f3f9d3/p`; the package contained `lib/libsee.so` (42,240 bytes) and `licenses/LICENSE` (11,357 bytes), plus Conan metadata (4 files total in the baseline).
  `sha256sum lib/libsee.so` returned `8792f0df0890ebeadc4c69eef63aa00fe69cdb3b857d03c7722417cabf23fbfd`.

## L2: ✅ PASS
  The package is a shared diagnostic library and has no executable under `bin/`; binary `--version` smoke testing is therefore not applicable. Its real runtime smoke test is the recorded consumer plus `LD_PRELOAD=/storage/Users/currentUser/.conan2/p/b/libsef0826f2f3f9d3/p/lib/libsee.so /data/service/hnp/bin/bash -c true`, which exited 0.

## L4: ✅ PASS
  `readelf` on the actual AArch64 DSO reported `Type: DYN`, a non-executable `GNU_STACK` (`RW`), `GNU_RELRO`, and `BIND_NOW`/`NOW` dynamic flags. The package has NX, full RELRO and the expected DSO `DYN` type; PIE is not separately applicable to a shared object.

## L5: ✅ PASS
  A first-run baseline was generated from the actual package folder (`files=4`), then immediately compared against the same package: `baseline compare: files=4 added=0 removed=0 modified=0`. The raw baseline is retained locally at `reports/baseline.json` and is ignored as a generated artifact.

The original `conan-verify` cache lookup was not used to manufacture PASS: its Conan-2 JSON lookup could not discover the package ID. The G4/L2/L4/L5 results above are the independently executed, package-path-bound checks and are recorded with their actual outputs; no unavailable check is silently counted.
