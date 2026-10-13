# google-sparsehash 2.0.4 OHOS Conan migration

## Scope

This change adapts upstream sparsehash/sparsehash 2.0.4 as the new package
name `google-sparsehash` for the HarmonyOS PC Conan pipeline. The archive
already ships `sparsehash/2.0.4` under the upstream package name; this
recipe provides the `google-sparsehash` alias required by downstream
consumers that reference the Google-era project name. The package is
header-only and has no third-party Conan dependencies.

## Source and compatibility

The recipe downloads the official `sparsehash-2.0.4` tag from GitHub
codeload and verifies SHA256
`8cd1a95827dfd8270927894eb77f62b4087735cbede953884647f16c521c7e58`.
An explicit `filename` is required because the codeload URL does not end
in an archive extension; without it Conan attempts ZIP extraction and
raises `BadZipFile`.

Upstream normally generates `sparsehash/internal/sparseconfig.h` and
`src/config.h` through Autotools. The recipe writes equivalent target
headers for Linux/OHOS using only verified standard C/C++ and POSIX
features. The sole source patch replaces `u_int16_t` with standard
`uint16_t` in `sparsehashtable.h` (OHOS musl does not provide the BSD
spelling) and makes the upstream `hashtable_test` honor `TMPDIR`
instead of hardcoding the read-only `/tmp`. The remaining legacy uses in
`sparsetable` are covered by upstream's `HAVE_UINT16_T` compatibility
typedef. No upstream assertions are modified and no OHOS-specific
platform macros are introduced.

## Validation

- `conan create` completed for OHOS 6.0, armv8, Clang 15, libc++, C++17,
  on the native HarmonyOS PC (aarch64) device. Package id
  `6b129b068851896169fae42d399fa922d239ce8a`, recipe revision
  `6259ef895eded8347a246cfa3643a553`, package revision
  `a79ac1a06a7622d29b855e72b6d15813`.
- All seven upstream programs were compiled from the patched source tree
  and executed on the device inside `conan create` build(), each
  returning zero: `template_util_unittest`, `type_traits_unittest`,
  `libc_allocator_with_realloc_test`, `sparsetable_unittest`,
  `hashtable_test`, `simple_test`, `simple_compat_test`.
- The package contains both `sparsehash/` and legacy `google/` include
  trees, the generated target `sparseconfig.h`, and the BSD license.
- `test_package` exercised `sparse_hash_map`, `dense_hash_map`,
  `sparse_hash_set`, and `dense_hash_set` through the generated
  `google-sparsehash::google-sparsehash` CMake target: insertion
  (operator[]/insert), lookup (find/count), erase, iteration sums,
  resize, and clear — 45 static assertions, 1060 runtime checks.
  Dense containers use the documented API contract: `set_empty_key`
  before any use and `set_deleted_key` before erase.
- `test_ohos` (HarmonyOS PC special) compiled the packaged headers with
  the real OHOS clang through both public include trees, verified the
  test binary as ELF64 AArch64 via readelf, and ran semantics the base
  tests do not cover: string keys with `std::hash`, 5000-element growth
  across sparse groups (DEFAULT_GROUP_SIZE = 48), and dense
  insert/erase churn forcing internal resize — 18 static assertions,
  2683 runtime checks. The package is header-only and produces no ELF
  library, so no library-artifact check is claimed.

## Relationship to sparsehash/2.0.4

Both recipes package the identical upstream tarball with the same patch
set; `google-sparsehash` exists because downstream projects reference
the Google-era name. No existing archive depends on the new package
name yet, so introducing it creates no conflicts with the already
published `sparsehash/2.0.4`.

## Knowledge reference

The verified E216 draft (`knowledge/graph/draft/E216-draft-CX17.kv`
and `.md`) documents the reusable cross-compilation rule that generated
configuration headers must describe the OHOS target rather than the
Windows build host, including generation, target-compiler verification,
and device-runtime verification.
