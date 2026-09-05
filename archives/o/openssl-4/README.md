# OpenSSL 4 for HarmonyOS

## 概述

OpenSSL 4.x 系列（`openssl-4` 包）在 HarmonyOS/OpenHarmony (aarch64) 上的编译和测试记录。

**注意**：`openssl-4` 与 `openssl`（1.1.1/3.x 系列）是**不同的 Conan 包名**，对应上游
OpenSSL 4.x 大版本独立成包，两者可在同一项目中并存。下游如需 OpenSSL 4 的新 API
（ECH、ML-DSA、QUIC 增强、SLH-DSA 等）应引用 `openssl-4/x.y.z`；仅需 3.x API 的继续
引用 `openssl/3.x`。

**可用版本**:
- **4.0.1** (首次适配): explicit getrandom entropy, static PIC package, musl-safe fd_set helper

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | OpenSSL 4 |
| 官网 | https://www.openssl.org/ |
| 源码 | GitHub Releases (openssl-4.0.1.tar.gz) |
| 许可证 | Apache-2.0 |

## OpenSSL 4.0.1 OHOS Conan 配方

- 构建系统仍是 Perl `Configure`（大写 C），`linux-aarch64` 内置 target
- `--with-rand-seed=getrandom` 显式选择内核熵源，排除 `DEVRANDOM_WAIT`/`FD_SET` 代码路径
- `no-asm`（E006）、`no-shared`、`no-legacy`、`no-module`、`no-docs`、`no-pinshared`、`-fPIC`
- `no-pinshared` 为 4.0 新选项：静态构建默认仍会为 libcrypto/libssl 加 pin 链接标记，
  与 `no-shared` 一起配置以避免第三方共享库被意外 pin
- 4.0 移除 engines（`ENGINESDIR` 不复存在，`no-engine` 恒为禁用态）；`install_sw`
  分解为 `install_dev`/`install_modules`/`install_runtime`
- musl 可移植性补丁两枚（按 4.0.1 上下文重新生成）：`apps/speed.c` 改走
  `openssl_fdset` 有界助手；`include/internal/sockets.h` 在 `__MUSL__` 下用
  `fds_bits` 布局实现该助手（不依赖 SDK 私有 `__fd_chk` 符号）

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS PC (HongMeng Kernel) |
| 架构 | aarch64 |
| 编译器 | clang 15.0.4 (aarch64-linux-ohos target) |
| 工具链 | llvm-ar, llvm-ranlib, llvm-nm |
| 构建 | make -j1（HMDFS 并行竞争规避） |

## 与 openssl 3.x 系列（openssl 包）的关系

| 维度 | openssl (3.x) | openssl-4 (4.x) |
|------|---------------|-----------------|
| 包名 | openssl | openssl-4 |
| ENGINESDIR | /lib/engines-3 | （已移除 engines） |
| engine API | 可用（已弃用） | 移除（恒 no-engine） |
| SSLv3/SSLv2 ClientHello | 兼容代码存在 | 移除 |
| ECH (RFC 9849) | 无 | 支持 |
| QUIC | 支持 | 增强（默认启用） |
| 共享库版本 | libssl.so.3 | libssl.so.4（SHLIB_VERSION=4） |

## 经验总结

1. **并行构建陷阱**：HMDFS 上 `make -jN` 会因 `.d.tmp` 的 mv 竞争随机失败，必须 `-j1`
2. **fd_set 可移植性**：musl 的 `FD_SET` 检查宏引用 SDK 私有 `__fd_chk`，跨 SDK 版本
   有差异（3.5.6 时代缺失），`__MUSL__` 守卫的 `fds_bits` 直写实现可彻底回避
3. **测试边界**：交叉构建只证明上游测试程序和真实 consumer 可编译/链接；目标端执行
   必须在 `can_run=true` 时另行取证
