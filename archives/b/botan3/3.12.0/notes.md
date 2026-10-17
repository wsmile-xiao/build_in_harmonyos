# botan3 3.12.0

Botan 3.12.0 is built with its bundled Python `configure.py` (custom build
system, not CMake/Autotools). The recipe requests a static library only and
packages the generated `libbotan-3.a` plus the public headers in upstream's
installed layout `include/botan-3/botan` (configure stages them under
`build/include/public/botan`; symlinks are dereferenced during packaging).

## OHOS armv8 real-machine validation (2026-09-08)

`conan create` + `test_package` on the device completed with exit code 0:

- `libbotan-3.a` (26 MB, 500+ objects, `make -j1`)
- 181 public headers under `include/botan-3/botan`
- `test_package` **2/2 Passed** on device:
  - `botan3_sha256`: SHA-256 digest of a fixed payload asserted
    byte-for-byte + hex codec round-trip
  - `botan3_aes_gcm`: consumer scenario — AES-256-GCM encryption against
    NIST GCM Test Case 14 (known-answer ciphertext+tag), authenticated
    decryption round-trip, tampered-tag rejection (6 assertions total)

## Adaptation decisions

Botan has no external dependencies (W0: nothing to resolve; optional
compression/sqlite modules are not enabled), so the whole adaptation is
toolchain-driven. Everything below was verified on device, most of it with
minimal reproducer programs before being folded into the recipe:

1. **`--os=linux --cpu=arm64`** — Botan's build-data has no OHOS target;
   the Linux musl environment is close enough, same approach as the
   validated botan2/2.19.5 recipe.
2. **`--without-os-features=explicit_bzero`** — OHOS musl libc does not
   provide `explicit_bzero`. Upstream `mem_utils.cpp` already has a
   portable fallback (memset through a volatile function pointer, verified
   by upstream for aarch64), which this configure flag selects by keeping
   `BOTAN_TARGET_OS_HAS_EXPLICIT_BZERO` out of the generated `build.h`.
   Zero-patch replacement for the manual build.h edit used by the earlier
   botan 3.6.1 manual build.
3. **`--cc-abi-flags=-march=armv8.2-a+crypto+sha3+sm4`** — see patch 0004:
   Botan 3.12 tags crypto kernels with function-level `target(...)`
   attributes whose intrinsics stay macro-gated (OHOS clang-15), so the
   features must also come from the command line. clang-15 rejects
   `+sha512` as an extension name but `armv8.2-a+crypto+sha3+sm4` makes
   every intrinsic the library uses visible (AES/GHASH/SHA512/SM4 all
   verified with on-device test programs).
4. **`--disable-modules=kyber,kyber_90s,kyber_common,kyber_round3,ml_kem,
   dilithium,dilithium_aes,dilithium_common,dilithium_round3,ml_dsa`** —
   the StrongSpan-heavy Kyber/Dilithium family (including the ML-KEM /
   ML-DSA modules layered on the same `*_common` code) does not compile
   under the OHOS clang-15 toolchain; the botan 3.6.1 adaptation recorded
   the same failure. `dilithium_shake` is auto-dropped as a dependent.
   Other PQ modules that also use StrongSpan (frodokem, classic_mceliece,
   sphincsplus, xmss) compile fine and stay enabled. Revisit once the
   toolchain moves past clang 15.
5. **`--build-targets=static,tests` + `make -j1 check`** — the upstream test
   binary IS built and the full suite runs inside `conan create` (initially
   the run skipped it: test sources use `std::ranges::sort/equal/find`, 12
   call sites, that OHOS clang-15 libc++ does not ship; patch 0003 rewrites
   them with iterator-based algorithms, same approach as patch 0002 for the
   library). `make check` invokes `./botan-test` with the absolute
   `--data-dir` recorded in `build_config.json`, and the recipe exports
   `TMPDIR=<build_folder>` for it because patch 0005 redirects the test
   runner's mkstemp away from the read-only `/tmp` (same as the merged
   botan2/2.19.5 recipe). Test-case counting (registration-entry metric,
   matches the PR review tool): 396 source registration sites upstream
   (BOTAN_REGISTER_TEST 363 + BOTAN_REGISTER_TEST_FN 33; 122 is the module
   FILE count, not the case count); our build compiles in 367 and make check
   passes all of them (CI #45634); 29 sites are compiled out by gating —
   test_kyber 8 + test_dilithium 4 + test_ml_dsa 1 + test_tls_hybrid_kem_key 1
   for the disabled Kyber/Dilithium modules, and test_tpm 2 + test_tpm2 8 +
   unit_asio_stream 1 + test_compression 3 + test_jitter_rng 1 for external
   dependencies / optional framework modules that configure auto-skips.
6. **`--link-method=copy`** — Botan's configure prefers symlinks when the
   host supports them, but the device's /storage (hmdfs) refuses symlink
   creation (`[Errno 13] Permission denied`); copy mode sidesteps it.
7. **`make -j1` + archive recovery** — single-threaded build for
   reproducibility with the validated botan2 run and to keep the device's
   memory headroom comfortable (peak MemAvailable never dropped below
   ~12.7 GB of 32 GB). Botan's Makefile issues one very long
   `ar crs libbotan-3.a <all .o>` command that OHOS toybox shell truncates
   silently; when `libbotan-3.a` is missing after make, the recipe
   recreates it with a short glob command
   (`ar crs libbotan-3.a build/obj/lib/*.o`). In the successful run the
   archive was produced by make itself.
8. **Patches 0001/0002/0004** — see conandata.yml for the detailed
   rationale (missing `std::array` spaceship / missing
   `ranges::equal|any_of` / broken multi-feature `target` attributes in
   OHOS clang-15's trimmed libc++).
9. **test_package C++20** — the shared ohos-aarch64 profile defaults to
   `cppstd=17`; Botan 3 headers require C++20, so the test declares
   `CMAKE_CXX_STANDARD 20` + `target_compile_features(cxx_std_20)`.

## Build-run history on device (for future reference)

| run | failure | fix |
|-----|---------|-----|
| 1 | configure: symlink EACCES on /storage | `--link-method=copy` |
| 2 | `vaesdq_u8` undeclared (macro-gated intrinsics) | global `-march=armv8.2-a+crypto+sha3+sm4` |
| 3 | `operator<=>` implicitly deleted (std::array has no spaceship) | patch 0001 |
| 4 | `std::ranges::equal` missing | patch 0002 (first half) |
| 5-6 | always_inline `+simd` mismatch despite attribute fix (clang-15 parses multi-feature target attributes wrongly; verified with minimal reproducers) | patch 0004 (disable BOTAN_FUNC_ISA attributes) |
| 7 | more `ranges::equal`/`any_of` users (certstor*, x509_crl, x509path) | patch 0002 v2 (12 call sites) |
| 8 | headers staged under `build/include/public/botan`, not `build/include/botan-3` | package() → `include/botan-3` upstream layout + `cpp_info.includedirs` |
| 9 | test compiled as C++17 (`concept` errors) | CMAKE_CXX_STANDARD 20 in test_package |
| 10 | test bug: `hex_decode` returns `vector`, assigned to `string` | fixed test source |
| 11 | **green: conan create exit 0, test 1/1 passed** (no upstream suite yet) | — |
| 12 | upstream tests enabled: 0003 patch (12 ranges sites in tests) + 0005 tmpdir port; `--build-targets=static,tests` + `make -j1 check` with TMPDIR=build_folder | verified in the PR CI build |
| 13 | CI #43458: `test_stdout_reporter.cpp:90` `m_out << "\n"` fails — "invalid operands … incomplete type 'std::ostream'": the runner/test TUs only include `<iosfwd>` and OHOS libc++15's thin transitive includes never complete the type (upstream gets it transitively). Same latent class in test_asn1/test_bigint/test_pubkey/test_tls (stringstreams without `<sstream>`) | patch 0006: add `<ostream>`/`<sstream>` to the five TUs |
| 14 | CI #44821 (~2.5h in, deep in the test TU sequence): `test_octetstring.cpp` passes `Botan::OctetString` to `test_bin_eq(std::span, std::span)` — pre-LLVM-16 libc++'s span container constructor requires `.data()` (OctetString only has begin()/end()); newer libcs convert via the ranges-based ctor | patch 0007: explicit `as_span()` bridge (iterator-pair span ctor) at the 7 call sites |
| 15 | CI #44907 (compile reached test_srp6.cpp, i.e. a–r clean): same span class via `SymmetricKey` (= alias of OctetString; the 0007 sweep had grepped the literal name only). srp6_client_agree()/step2() results compared with test_bin_eq | patch 0008: helper-level `test_bin_eq(string_view, OctetString, OctetString)` overload in tests.h/tests.cpp — covers all remaining and future call sites (type-swept the other 12 SymmetricKey-using files: all pass vectors/`bits_of()`/lib APIs only) |
| 16 | CI #44994: 0008 v1 declared the overload with unqualified `OctetString` inside `namespace Botan_Tests` while the forward declaration lives in `namespace Botan` → "unknown type name 'OctetString'" in every TU including tests.h | 0008 v2: add `using Botan::OctetString;` right after the BigInt using-declaration (same import pattern tests.h already uses) |

## Reproduce

On the device (isolated CONAN_HOME + offline download cache, see
`botan3-setup.sh`/`botan3-run.sh` approach used for the validated run):

```bash
conan create archives/b/botan3/3.12.0 \
  -pr:h ohos-aarch64 -pr:b ohos-aarch64 --build=missing
```

On the build host via shadow CI:

```bash
CI_PACKAGES="archives/b/botan3/3.12.0" zsh ci/conan/build_and_test.sh
```
