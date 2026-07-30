# sparsehash 2.0.4 OHOS Conan migration

## Scope

This change migrates the existing header-only Sparsehash archive to the Conan
pipeline. It is a prerequisite for the graph-tool 2.98 adaptation.
The package has no third-party Conan dependencies.

## Source and compatibility

The recipe downloads the official `sparsehash-2.0.4` tag from GitHub codeload
and verifies SHA256
`8cd1a95827dfd8270927894eb77f62b4087735cbede953884647f16c521c7e58`.
An explicit `filename` is required because the codeload URL does not end in an
archive extension; without it, Conan attempts ZIP extraction and raises
`BadZipFile`.

Upstream normally generates `sparsehash/internal/sparseconfig.h` and
`src/config.h` through Autotools. The recipe writes equivalent target headers
for Linux/OHOS using only verified standard C/C++ and POSIX features. The sole
source patch replaces `u_int16_t` with standard `uint16_t` in
`sparsehashtable.h`; the remaining legacy uses in `sparsetable` are covered by
upstream's `HAVE_UINT16_T` compatibility typedef.

## Validation

- `conan create` completed for OHOS 6.0, armv8, Clang 15, libc++, C++17.
- Seven upstream programs compiled and linked as AArch64 ELF executables:
  `template_util_unittest`, `type_traits_unittest`,
  `libc_allocator_with_realloc_test`, `sparsetable_unittest`,
  `hashtable_test`, `simple_test`, and `simple_compat_test`.
- The package contains both `sparsehash/` and legacy `google/` include trees,
  the generated target `sparseconfig.h`, and the BSD license.
- A real consumer using `sparse_hash_map` and `dense_hash_map` compiled and
  linked against the generated `sparsehash::sparsehash` CMake target.

All eight AArch64 executables were then transferred to a HarmonyOS PC with
per-file SHA256 verification, signed in place at their final HMDFS paths, and
executed with a writable `TMPDIR`. The seven upstream programs and the Conan
consumer all returned zero (8/8). The consumer printed
`sparsehash consumer test passed`; its unsigned and signed SHA256 values were
`507b7a2bca25c8e6286fd4290d94d61565841a8688ae586383f403fbf40dd1ac` and
`9003ab7fdfb1795b2b8cd668f06deb02fbbe29e4b0d128dd23c3e79ceeaa9718`.

## Knowledge reference

This adaptation adds the verified E216 draft
(`knowledge/graph/draft/E216-draft-CX17.kv` and `.md`). It documents the
reusable cross-compilation rule that generated configuration headers must
describe the OHOS target rather than the Windows build host, including
generation, target-compiler verification, and device-runtime verification.
