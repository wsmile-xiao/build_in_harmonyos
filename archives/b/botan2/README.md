# Botan 2

Botan is a C++ cryptography library providing hash functions, symmetric and
public-key algorithms, certificates, and TLS support.

Version `2.19.5` is packaged as a static Conan library for OHOS `armv8`.
The recipe executes Botan's native `make check` target and the consumer test
verifies a SHA-256 digest through the public C++ API.
