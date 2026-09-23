# libcrypto3

OpenSSL libcrypto component packaged as a standalone Conan library.

## Description
libcrypto3 provides the OpenSSL `libcrypto` library (cryptographic primitives:
AES, RSA, SHA, HMAC, RAND, etc.) without the `libssl` TLS/SSL layer. This is
useful for consumers that only need cryptographic functionality without TLS.

## Source
Built from the official OpenSSL source releases:
- https://www.openssl.org/
- https://github.com/openssl/openssl

## Relationship to openssl package
The `openssl` Conan package exports both `libssl` and `libcrypto`.
The `libcrypto3` Conan package exports only `libcrypto`.
Both use the same OpenSSL source code, build method, and patches.

## Build
- Build system: custom-perl (Configure + make)
- Static-only (no-shared, R26 system-name library)
- Target: linux-aarch64
- no-asm (OHOS platform limitation)
