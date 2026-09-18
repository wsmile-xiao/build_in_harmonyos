# libosmocore

## 简介

Osmocom 核心库，为 GSM/UMTS/GPRS 协议栈与电信信令提供基础 C 库集合，
包含 libosmocore、libosmovty、libosmogsm、libosmogb、libosmosim、libosmousb、
libosmoctrl、libosmocodec、libosmocoding、libosmoisdn 共 10 个库，
并提供 osmo-aka-verify、osmo-auc-gen、osmo-arfcn、osmo-config-merge 等命令行工具。

## OHOS 适配

- 使用原生 TLS（`-fno-emulated-tls`）：emutls 无法跨 DSO 传递 `osmo_ctx` 上下文，运行时段错误
- `config.guess` / `config.sub` 补齐 `aarch64-linux-ohos` 平台三元组（E007/E114）
- `sockaddr_storage` 与平台头文件重定义冲突，改用平台中立宏守卫（E091）
- musl 缺少 glibc 的 `__always_inline` 宏，`include/osmocom/core/hash.h` 改为平台中立写法
- 上游 1.11.0 tarball 缺 `src/gsm/kdf/crypto.h`，按上游同版本 tag 原文补齐
- 内核无 SCTP 能力时，上游测试用例自带跳过逻辑生效（`AT_SKIP_IF`）

## 依赖

- talloc / libmnl / pcsc-lite / libusb（均为制品仓预编译包）
- `liburing` 不引入：平台 seccomp 拦截 io_uring，配方以 `--disable-uring` 关闭该可选后端

## 功能验证

- 上游测试：上游测试实体共 **95 项**（`tests/Makefile.am` 的 `check_PROGRAMS` 94 个测试程序 + 1 个集成脚本 `osmo-auc-gen_test.sh`），**零删减**；Autotest 套件 `tests/testsuite.at` 的 90 个 case 中执行 88 项、通过 88 项、0 失败，2 项跳过（SCTP 内核不支持、io_uring 被 seccomp 拦截；均由上游 `AT_SKIP_IF` 条件跳过）
- 鸿蒙专有测试：`test_package/test_ohos_tls.c`，验证 `osmo_ctx` 上下文经原生 TLS 跨 DSO 可正常访问

## 参考

- 上游项目：https://osmocom.org/projects/libosmocore
- 源码归档：https://downloads.osmocom.org/releases/libosmocore/libosmocore-1.11.0.tar.bz2
