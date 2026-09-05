# OpenSSL 4.0.1 Test Report

## Test environment

- Build host: OpenDesk worker (aarch64 OHOS device, can_run=true)
- Target: HarmonyOS PC aarch64 (OHOS 6.0, musl, clang 15.0.4)
- Conan profile: ohos-aarch64 (os=OHOS arch=armv8 compiler=clang 15)
- Package: openssl-4/4.0.1@ohpcd/stable

## Upstream test suite (make test)

The recipe builds all upstream software and test programs
(`make -j1 build_sw build_tests`) and runs the upstream test suite in-place
(`HARNESS_JOBS=1`) because Conan reports `can_run=true` on this device.

Harness summary (both verification runs identical):

```text
Files=363, Tests=4079, 1250 wallclock secs
Result: PASS
```

Breakdown per test script (363 files include 1 NOTESTS harness file):

| Outcome | Scripts | Notes |
|---------|---------|-------|
| ok      | 309     | passed on device |
| skipped | 53      | all build-option gated |
| failed  | 0       | — |

Skipped reasons (all expected for this configuration, none musl/OHOS-specific):
FIPS-only tests (non-fips build), Windows-only registry tests, enable-tfo,
rc5 (not supported), LMS (not supported in this build), legacy-PBE
(no-legacy), ACVP, compression algorithms, etc.

## test_package (Conan consumer)

`conan create` ran the explicit test package:

1. `./test_openssl` — C consumer:
   - `OpenSSL_version()` contains "4.0.1"
   - `RAND_bytes()` 32 bytes succeeds (real entropy backend, getrandom)
   - `SHA256("OpenSSL OHOS consumer")` matches the fixed known answer
     (`42bdab88...040f6393`) via `CRYPTO_memcmp`
   - `SSL_CTX_new(TLS_method())` creates and frees a TLS context
   - Result: **passed** ("OpenSSL version, RAND, SHA256, and TLS context
     checks passed")
2. `sh test_openssl_cli.sh` — CLI checks:
   - `openssl version -a` reports "OpenSSL 4.0.1"
   - `OPENSSLDIR: "/ssl"` exact match
   - `MODULESDIR: "/lib/ossl-modules"` exact match (ENGINESDIR intentionally
     absent — engines removed in OpenSSL 4.0)
   - `dgst -sha256` of "abc" matches
     `ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad`
   - `rand -hex 16` produces 32 lowercase hex chars
   - Result: **passed** ("OpenSSL CLI version, path, SHA-256, and random
     checks passed")

## Static analysis of the produced package

- `llvm-nm -u`: zero `__fd_chk` references in `libcrypto.a`, `libssl.a`,
  the packaged CLI, and all apps objects
- Package contents: 150 files — 2 static archives, 1 CLI, headers, licenses;
  no `.so`, no upstream `.cmake`/`.pc`
- CLI on-device run confirms `Seeding source: getrandom-syscall`

## Conclusion

All planned tests passed: upstream suite 4079/4079 (PASS, 0 failed),
consumer 4/4 assertions, CLI 6/6 assertions. No musl/OHOS-specific failures
were observed; all 53 skips are upstream build-option gates.
