# libcotp 4.2.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-26
- 编译器: clang/clang++
- 状态: built

## 上游核实

| 项 | 值 |
|---|---|
| 上游仓库 | https://github.com/paolostivanin/libcotp |
| release/tag | v4.2.1 |
| source URL | https://github.com/paolostivanin/libcotp/archive/refs/tags/v4.2.1.tar.gz |
| sha256 | 5f0cc41049e9fa296c1edf09c6fb0bb6dae588b149d5049adbc41d21aefc1bb1 |
| license | Apache-2.0 |
| 原生构建系统 | CMake (cmake_minimum_required 3.16) |
| 对外公开 API | src/cotp.h（get_totp / get_hotp / get_steam_totp / get_yaotp / base32_encode / cotp_ctx_* / cotp_strerror / otp_to_int 等） |

## 加密后端选择

上游 CMakeLists.txt 通过 `-DHMAC_WRAPPER=<gcrypt|openssl|mbedtls>` 选择 HMAC 后端：

| 后端 | 依赖链 | 仓库可用性 | 与 Conan CMakeDeps 兼容性 |
|---|---|---|---|
| gcrypt | libgcrypt + libgpg-error（自带 FindGcrypt.cmake） | 有 libgcrypt/1.12.2 + libgpg-error/1.55 | 需手工注入 GCRYPT_* 变量或 patch Find 模块 |
| **openssl** | openssl/3.5.6 | **已有** | **CMake 原生 find_package(OpenSSL)，CMakeDeps 直接生成 OpenSSL:: 目标，零 patch** |
| mbedtls | mbedtls（自带 FindMbedTLS.cmake） | 有 mbedtls/3.6.6、4.1.0 | 需 patch Find 模块或手工注入变量 |

选 **openssl**：依赖最短、已可用、与 CMake 原生 `find_package(OpenSSL)` 完全对接，无需任何 patch。

## 构建步骤

1. 下载源码：https://github.com/paolostivanin/libcotp/archive/refs/tags/v4.2.1.tar.gz
2. Conan `get()` 解压（strip_root）
3. CMakeToolchain 生成工具链（OHOS aarch64 交叉编译）
4. cmake 配置（关键 option 见下）
5. cmake --build
6. cmake --install 到 package_folder

### 关键 CMake option（均为上游真实 option）

| Option | 值 | 说明 |
|---|---|---|
| `HMAC_WRAPPER` | openssl | 选择 OpenSSL HMAC 后端 |
| `BUILD_SHARED_LIBS` | ON | 构建共享库（libcotp.so，SOVERSION=4） |
| `BUILD_TESTS` | OFF | 关闭上游 Criterion 测试套件（由 test_package 替代） |
| `COTP_ENABLE_VALIDATION` | OFF | 默认关闭校验 API（可选开启） |
| `COTP_BUILD_FUZZERS` | OFF | 关闭 libFuzzer harness（开发者专用） |
| `CMAKE_INSTALL_LIBDIR` | lib | 保持扁平安装布局 |

## Linux-only API 分析

libcotp 是纯 C 库，对系统 API 的依赖极小：

| 类别 | 实际使用 | OHOS 兼容性 |
|---|---|---|
| time | `get_totp()` 内部 `time(NULL)` | OK — OHOS libc 提供 time(2) |
| random | 无 | 不涉及 |
| endian | 手工字节序处理（OTP 截断） | OK — 不依赖 `<endian.h>` 扩展 |
| socket | 无 | 不涉及 |
| pthread | 无直接调用 | OK（OpenSSL 的 -lpthread 由 openssl recipe 的 system_libs 提供） |
| explicit_bzero | `check_function_exists(explicit_bzero)` 检测，缺失则用 volatile 回退 | OK — 有 fallback |

结论：**零 patch**，无需任何平台适配补丁。

## 遇到的问题与解决方案

无。上游 CMakeLists.txt 在 OHOS clang 下直接构建通过。

## 验证结果

test_package 使用真实公开 API（get_hotp / get_totp_at / base32_encode / otp_to_int / cotp_strerror），
对 RFC-4226 Appendix D（HOTP）和 RFC-6238 Appendix B（TOTP）的已知答案向量做断言：

- HOTP counter 0→755224, 1→287082, 2→359152, 3→969429
- TOTP T=59→94287082, T=1111111109→07081804, T=1234567890→89005924
- otp_to_int("07081804")→7081804
- cotp_strerror(NO_ERROR) 非 NULL

## 源码修改

无（零 patch）。

## 依赖版本

- openssl/3.5.6（HMAC 后端）

## 交付物

- `conanfile.py` — Conan recipe（CMake + OpenSSL 后端，OHOS 交叉编译）
- `conandata.yml` — 源码与 sha256
- `test_package/` — 真实 API 功能测试
- `manifest.yaml` / `README.md` / `notes.md` — 元数据与文档

---

**最终状态**: built
