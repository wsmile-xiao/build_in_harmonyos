# InChI 1.07.5 adaptation notes

## Scope

- Contributor task: `5841`, activity `开源鸿蒙PC专项积分赛-依赖`.
- Owner: `2301_80739235`, team `天天开心`.
- Branch: `feat/inchi-1.07.5`.
- Source: official `v1.07.5` GitHub release archive, 109621215 bytes,
  SHA-256 `9a8af985295c47bfaf424ad8386b1597da515589665ec71908dae1bd2b67ac96`.
- Build dependency: `gtest/1.17.0`, resolved from `ohpcd` with RREV
  `ab1bc3bf51522490eef07a83c2dbd203`, PID
  `21b17f8b2bc0e9511e276e3d57a23893067cefe5`, and PREV
  `489a70cbb1156b4d5594f8ce638b9630`.

## Build decisions

- Replace top-level `FetchContent` with `find_package(gtest CONFIG REQUIRED)`
  so the recipe never downloads an undeclared dependency during the build.
- Provide a private `inchi_gtest_main.cpp` because the published gtest recipe
  exports `gtest::gtest` but not `gtest::gtest_main`. Its name deliberately
  does not match upstream's `test_*.cpp` source glob.
- Build the API shared library and complete unit-test inventory with
  `INCHI_BUILD_CLI=OFF` and `BUILD_TESTING=ON`.
- Extend upstream's non-Windows/non-Apple CMake branch to OHOS and set
  `LINKER:-soname,libinchi.so`; disable RPATH and RUNPATH.
- Package `libinchi.so`, `inchi_api.h`, and `ixa.h`; export CMake target
  `inchi::inchi` and pkg-config module `inchi`.

## Cross-build evidence

The isolated r11 `conan create` completed 132 compile/link steps. The package identity is
RREV `90f05836caf65e6a83041bc99d3fa394`, PID
`6b129b068851896169fae42d399fa922d239ce8a`, PREV
`7006329b38ea6e34c345a9658c97f4b4`. All seven upstream executables, the
consumer, and `libinchi.so` are AArch64 ELF files. They contain no
RPATH/RUNPATH and no path-valued NEEDED entries. `libinchi.so` has the expected
SONAME; the dependency union is `libc.so`, `libinchi.so`, and
`libc++_shared.so`.

Raw build stderr SHA-256:
`d42428bf0495d61bc2f3ce92be250555faa4bdf955f4a955ca2cd1319d77b4cf`.
W3 payload manifest SHA-256:
`e0671858f4aa21fe5dfd67d1d6ff2e20e6aa13c4481acab6cbe30699805716b8`.

## Target validation and recovery

The first immutable W3 run (`inchi-1.07.5-w3-r1`) completed exact-byte
transfer, native self-signing, and one launch, then failed at consumer check 1.
`CheckINCHI(water_inchi, 1)` selected the API's strict InChI-to-InChI
round-trip and byte-equality mode, while the assertion intended only to classify
the standard layout. The upstream header explicitly states that strict mode
may produce a false alarm. The successor changed only this argument to `0`,
rebuilt the consumer, and retained all six functional assertions.

The create-new r2 transaction first passed the corrected consumer, but its
recipe identity became stale after the export-source and license fixes. The
r3 transaction rebuilt that recipe, then the official G1 gate showed that the
class attribute did not provide the required `export_sources()` method
contract. The create-new r4 transaction rebuilt the method-based final recipe
and passed consumer 1/1 with 6/6 API assertions,
upstream executables 7/7, 59 runtime GoogleTest cases, and post-test signed ELF
state 10/10. Its 12-phase receipt chain binds candidate code tree
`c52b9bed9896471f7d7e923963a4ebba62ef4783`, endpoint, boot ID, UID, package
identity, runner/controller/validator hashes, and `launch_count=1`. Release and
independent postrelease readback prove the task process and remote root absent.

The submitted transaction result is
`reports/w3-transaction-result.json` with SHA-256
`01809a9efb0dd322b2ea0f6a87ed21c0659fba8b84e67da58f0df9641681199e`.

## Safety boundaries

- The static source count of 497 assertion tokens is inventory metadata, not a
  claimed runtime assertion denominator.
- The official native signer is used only under the unique task root; shared
  device tools and other task roots are untouched.
- A consumed W3 run is never relaunched. The r1 failure, stale r2/r3 passes,
  and current r4 pass remain separate immutable transactions.

### 对话 #1

- 2026-09-04: completed recipe adaptation, isolated Conan verification,
  immutable target validation, and submission-readiness evidence in this task.
- Reusable knowledge is captured by `E2175`; the `CheckINCHI` strict-mode
  behavior above remains version-level L3 evidence rather than a second
  reusable knowledge claim.
---

**编译结束**: 2026-09-04 06:18
**最终状态**: built
