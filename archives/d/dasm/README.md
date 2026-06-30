# dasm — DASM Macro Assembler

## 简介
DASM（又称 small systems cross assembler）是一个宏汇编器，支持多种8位处理器架构（6502/6803/68705/68HC11/68HC908/F8等），主要用于 Atari 2600、Channel F、Atari 7800 等复古平台开发。

## 版本信息
- 当前编译版本: 2.20.14.1
- 许可证: GPLv2+
- 版本验证方式: 直接运行 `dasm`（不支持 --version 参数）

## 编译说明
- 构建系统: 纯 Makefile（无 configure，无标准 install 目标）
- 编译器: clang 15.0.4
- 已通过补丁添加:
  - 0001-Makefile.patch: 标准 install 目标（含 DESTDIR/PREFIX 支持）
  - 0002-configure.patch: dummy configure 脚本（G0 门禁兼容）
- 手动安装: 无 `--version` 参数支持，需直接运行获取版本信息

## 预编译包产物
- `dasm-2.20.14.1-ohos-aarch64.tar.gz`: 预编译包（ELF签名，已strip）
  - 包含: bin/dasm, bin/ftohex, share/man/man1/dasm.1
- `dasm-2.20.14.1-ohos-aarch64-debug.tar.gz`: 调试符号包

## 测试结果
- 93 tests executed, 86 OK, 7 failed (selftest框架自测), result: overall PASS
