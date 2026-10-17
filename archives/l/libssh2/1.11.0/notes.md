# libssh2 1.11.0 — Conan 适配笔记

> 档案创建时间: 2026-04-25
> 最后更新: 2026-08-22 (Conan 适配完成)
> 状态: built (conan-verify 通过)

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | libssh2 |
| 版本 | 1.11.0 |
| 构建系统 | CMake |
| 源码 URL | https://www.libssh2.org/download/libssh2-1.11.0.tar.gz |
| SHA256 | 3736161e41e2693324deb38c26cfdc3efe6209d634ba4258db1cecff6a5ad461 |

## 二、Conan 适配

### 依赖
- openssl/3.5.6.1
- zlib/1.3.1.1

### 构建选项
- CRYPTO_BACKEND=OpenSSL
- ENABLE_ZLIB_COMPRESSION=ON
- BUILD_SHARED_LIBS=ON (默认动态)
- BUILD_STATIC_LIBS=OFF
- BUILD_EXAMPLES=OFF
- BUILD_TESTING=OFF
- ENABLE_WERROR=OFF
- CMAKE_POLICY_VERSION_MINIMUM=3.5 (libssh2 1.11.0 uses cmake_minimum_required(VERSION 3.1), CMake 4.x removed compat with <3.5)

### OHOS 平台适配
- ohos-cmake-rules.cmake: 设置 SONAME/RPATH/RPATH_ORIGIN 等 CMake 共享库变量
- OPENSSL_ROOT_DIR/INCLUDE_DIR/SSL_LIBRARY/CRYPTO_LIBRARY: 显式指定 OpenSSL 路径
- ZLIB_INCLUDE_DIR/ZLIB_LIBRARY: 显式指定 zlib 路径

### 配方验证结果
- G0: PASS (预构建风险评估)
- G1: PASS (配方完整性)
- G2: PASS (conan create 干净构建)
- G3: PASS (系统同名库隔离)
- G4: PASS (产物完整性)
- W3 本地 CI 模拟: PASS

## 三、对话记录

### 对话 #1 — 2026-08-22
**操作**: 基于 1.11.1 配方创建 1.11.0 conan 适配
**结果**: conan-verify 全部通过 (G1-G4 + W3)
**发现的问题**: CMake 4.x 不兼容 cmake_minimum_required(VERSION 3.1)，需设置 CMAKE_POLICY_VERSION_MINIMUM=3.5
**当前状态**: finish 完成，准备 submit
**遗留问题**: 无

## 结束

**编译结束**: 2026-08-22
**最终状态**: built (conan-verify 通过, W3 本地 CI 通过)

