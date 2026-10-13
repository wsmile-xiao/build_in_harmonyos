# google-sparsehash

Google sparsehash provides memory-efficient C++ `sparse_hash_map`,
`sparse_hash_set`, `dense_hash_map`, `dense_hash_set`, and `sparsetable`
containers. This package publishes the upstream 2.0.4 release under the
Google-era project name required by downstream consumers; it packages the
same upstream tarball as `sparsehash/2.0.4`.

## HarmonyOS adaptation

- Path A basic adaptation of the header-only upstream release; no binary
  library is produced and there are no third-party Conan dependencies.
- The recipe writes the `sparseconfig.h` and `config.h` headers that
  upstream Autotools would generate, describing the OHOS target rather
  than the build host.
- One patch with two narrowly scoped fixes: replace the BSD `u_int16_t`
  spelling with standard `uint16_t` in `sparsehashtable.h` (OHOS musl
  provides only the standard spelling), and make the upstream
  `hashtable_test` honor `TMPDIR` instead of hardcoding the read-only
  `/tmp`. No `__OHOS__` platform macro is introduced.
- All seven upstream test programs were compiled and executed natively on
  the HarmonyOS PC (aarch64) device inside `conan create`, each returning
  zero: 7/7 PASS.
- `test_package` verified real consumption of `sparse_hash_map`,
  `dense_hash_map`, `sparse_hash_set`, and `dense_hash_set` through the
  generated `google-sparsehash::google-sparsehash` CMake target.
- The HarmonyOS special test passed: the packaged headers were compiled
  with the real OHOS clang through both public include trees (`sparsehash/`
  and legacy `google/`), and the test binary was verified as ELF64 AArch64.

## References

- https://github.com/sparsehash/sparsehash
- https://github.com/sparsehash/sparsehash/releases/tag/sparsehash-2.0.4
