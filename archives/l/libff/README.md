# libff

libff is a C++ library for Finite Fields and Elliptic Curves, providing
the arithmetic layer for zk-SNARKs constructions: prime fields Fp and
their tower extensions (Fp2/Fp6/Fp12), elliptic curve groups G1/G2,
and bilinear pairings (Miller loop + final exponentiation).

## OHOS adaptation

- Builds the official v0.2.1 tag archive from scipr-lab/libff with CMake.
- Pins `CURVE=ALT_BN128`. The upstream default `BN128` is unusable here for two
  independent reasons (see notes.md for the full evidence chain):
  1. The official v0.2.1 tag tarball ships `depends/ate-pairing` and
     `depends/xbyak` as empty directories (git submodules are not included
     in tag archives), so the default configure fails outright.
  2. Even with both submodules restored at the exact gitlink-pinned commits,
     compilation fails on aarch64 at `zm2.cpp:3644` — the BN128 path is
     x86-64-only by design (Xbyak runtime JIT).
  ALT_BN128 is the same BN254 (alt-bn128/SNARK) curve with bit-identical
  q/r constants and cryptographically equivalent pairing values, but it is
  **not a drop-in equivalent**: `alt_bn128_*` vs `bn128_*`/`bn::Fp` are
  distinct, non-interchangeable C++ APIs with different object layouts
  (no ABI compatibility) and different stream serialization formats
  (cross-implementation data exchange must go through affine decimal text).
  Consumers must program against the `alt_bn128_*` API exported by this
  package; `cpp_info.defines=["CURVE_ALT_BN128"]` exposes the configuration.
- Disables `WITH_PROCPS` (OHOS has no libprocps); upstream provides the
  `NO_PROCPS` fallback in `libff/common/profiling.cpp`.
- Adds `CMAKE_POLICY_VERSION_MINIMUM=3.5` for CMake 4.x compatibility
  (upstream requires 2.8).
- Runs all 3 upstream ctest targets (bilinearity, groups, fields) in a
  separate Debug build tree without `-DNDEBUG`, because upstream tests
  use `assert()` as their oracle and would silently pass otherwise.
- test_package exercises the real core API: `alt_bn128_pp::init_public_params`,
  group/field arithmetic, `reduced_pairing` bilinearity and non-degeneracy,
  and stream serialization roundtrip.
- test_package_ohos (HarmonyOS-specific, 8 checks) verifies the actual
  platform-adaptation points: the `NO_PROCPS` profiling fallback at runtime,
  the aarch64-portable Montgomery Fp `invert`/`sqrt` paths, bigint↔mpz
  interop, bit-exact q/r constants, pairing determinism, zero-point
  serialization, and an object-level inspection of the in-package `libff.a`
  (parses the ar member table and ELF headers: all 24 objects must be
  ELF64/little-endian/ET_REL/EM_AArch64, the 5 `alt_bn128_*` curve objects
  must be present, and no x86-64-only `bn128_*` object may leak in).

## Dependencies

- `gmp/6.3.0.1` supplies GMP big integers (transitive headers:
  `libff/bigint.hpp` includes `gmp.h`).
- `openssl/3.5.6` aligns with upstream `find_package(OpenSSL REQUIRED)`.

## References

- https://github.com/scipr-lab/libff
