# libcotp 4.2.1

C library that generates TOTP and HOTP according to [RFC-6238](https://www.rfc-editor.org/rfc/rfc6238)
and [RFC-4226](https://www.rfc-editor.org/rfc/rfc4226), with Base32 codec
([RFC-4648](https://www.rfc-editor.org/rfc/rfc4648)), Steam Guard, YAOTP
(Yandex.Key) and `otpauth://` URI parser/builder.

## 功能概述

- HOTP（RFC-4226）与 TOTP（RFC-6238）生成，支持 SHA1/SHA256/SHA512
- 自定义位数（4–10）与周期（1–120 秒）
- Steam Guard TOTP 格式
- YAOTP（Yandex.Key）8 位字母码
- Base32 编解码
- `otpauth://` URI 解析与构建
- 可选的 TOTP 时间窗口校验（`-DCOTP_ENABLE_VALIDATION=ON`）
- 公共安全工具：`cotp_secure_memzero` / `cotp_timing_safe_memcmp`

## OHOS 适配

- 构建系统：CMake（上游原生）
- 加密后端：**openssl**（仓库已有 `openssl/3.5.6` Conan 包）
- 交叉编译：通过 Conan `CMakeToolchain` + `ohos-aarch64` profile，不依赖宿主机 /usr/lib 或宿主机 pkg-config
- 零 patch：上游 CMake 原生支持 OpenSSL 后端（`find_package(OpenSSL)`），与 Conan `CMakeDeps` 生成的 `OpenSSL::SSL` / `OpenSSL::Crypto` 目标直接对接

## 依赖关系

- C 编译器（clang）
- OpenSSL >= 3.0.0（HMAC 后端，由 `openssl/3.5.6` 提供）

## 参考资料

- 上游：https://github.com/paolostivanin/libcotp
- Release v4.2.1：https://github.com/paolostivanin/libcotp/releases/tag/v4.2.1
- License：Apache-2.0
