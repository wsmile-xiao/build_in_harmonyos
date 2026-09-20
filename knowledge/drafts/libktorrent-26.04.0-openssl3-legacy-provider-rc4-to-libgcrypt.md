# OpenSSL 3.x legacy provider 缺失致 RC4 消费库初始化必败（LibGcrypt 后端替代）

**素材来源**：libktorrent 26.04.0 适配（2026-09-20）

## 问题

OpenSSL 3.x 将 RC4 移入 legacy provider。ohpcd openssl/3.5.6.1 静态构建无
ossl-modules/legacy.so → `OSSL_PROVIDER_try_load("legacy")` 必返 null →
`bt::InitLibKTorrent()` return false → 全部调它的测试（10/38）在 initTestCase 集体失败。

## 修法（crypto 后端切换）

上游支持 USE_CRYPTO_BACKEND=LibGcrypt：
1. `tc.variables["USE_CRYPTO_BACKEND"]="LibGcrypt"` + `CMAKE_DISABLE_FIND_PACKAGE_OpenSSL=TRUE`
2. requires：openssl → libgcrypt/1.12.2（GCRY_CIPHER_ARCFOUR 原生 RC4）
3. 显式 requires libgpg-error/1.55 + CMAKE_CXX_FLAGS 注入其 include（gcrypt.h 引 gpg-error.h）
4. 切换后 38/38 全过（OpenSSL 后端实测 10 败复现）

## 适用判别

- 库的 crypto 用量 = RC4/DH/SHA1 级别 → LibGcrypt 完整覆盖，放心切
- 用 OpenSSL 特有 API（TLS/X509/ENGINE）→ 不可切，等 openssl 包补 legacy provider

## 连带影响

KTorrent6Config.cmake 的 find_dependency(OpenSSL/LibGcrypt) 分支随 USE_OPENSSL/USE_LIBGCRYPT
展开——消费者 test_package 需按实际后端桥接对应 target（conan 小写
libgcrypt::libgcrypt ↔ 上游大写 LibGcrypt::LibGcrypt）。
