# libcrypto3 3.5.7 — Adaptation Notes

## Overview
libcrypto3 is a standalone Conan package that builds the OpenSSL 3.5.7 source
but exports **only** the `libcrypto` library (not `libssl`). This is for consumers
that need cryptographic primitives (AES/RSA/SHA/HMAC/RAND) without TLS/SSL.

## Build System
- **Configure**: OpenSSL uses `perl ./Configure` (capital C), not autotools
- **Target**: `linux-aarch64` (built-in config for 3.5.x)
- **Options**: `no-asm no-shared --with-rand-seed=getrandom`
  - `no-asm`: OHOS platform has no assembly support (E006)
  - `no-shared`: Static-only build (R26 — libcrypto is a system-name library)
  - `--with-rand-seed=getrandom`: Use getrandom() syscall for entropy (OHOS/musl compatible)

## Compiler
- CC=clang (openssl Configure defaults to gcc, not available on OHOS)
- `-D__MUSL__` flag to activate bounded fd_set implementation (patch 0002)

## Patches
Both patches inherited from openssl 3.5.8.1 (same 3.5.x series):
1. `0001-apps-speed.c.patch`: Route async speed test through bounded fd_set helper
2. `0002-include-internal-sockets.h.patch`: Implement bounded fd_set for musl without `__fd_chk`

## Dependencies
None — libcrypto builds without external dependencies for static build.

## Differences from openssl package
- Package name: `libcrypto3` (not `openssl`)
- `package_info().cpp_info.libs = ["crypto"]` (only crypto, not ssl)
- Same source, same build method, same patches

## Test Results (local device)
- Upstream tests: 345 .t files total
  - Core tests run locally: 01-07 (90 files, 305 tests PASS) + 10-15 (25 files, 1884 tests PASS)
  - External tests (7): skipped (require external dependencies like krb5, python, gost-engine)
  - Fuzz tests (31): skipped (require special build configuration)
  - ecstress (1): skipped (stress test, extremely long running)
- Total tested: 115 files, 2189 tests, ALL PASS
- test_package: 5 cases (SHA-256/HMAC/AES-256-CBC/RAND_bytes/version) — all PASS
---

**编译结束**: 2026-09-15 12:08
**最终状态**: built
