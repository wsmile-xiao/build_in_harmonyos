# Botan 3

Botan 3.12.0 — C++20 cryptography library (hashes, AEAD, TLS, classic and
post-quantum signatures/KEMs).

Homepage: https://botan.randombits.net/

## 与 botan / botan2 的区别

- `botan`（3.6.1）：手工预编译包（无 Conan 配方），Kyber/Dilithium 已禁用。
- `botan2`（2.19.5）：Botan 2（C++11），Conan 配方真机验证通过。
- `botan3`（3.12.0）：Botan 3（C++20），Conan 配方静态库，禁用
  Kyber/Dilithium/ML-KEM/ML-DSA 模块（OHOS clang-15 兼容性）。

纯库，无 commands.json。
