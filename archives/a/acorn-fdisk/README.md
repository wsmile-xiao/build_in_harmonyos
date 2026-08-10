# acorn-fdisk

acorn-fdisk（上游项目名 arm-fdisk）是 Acorn/RISC OS 机器的磁盘分区编辑器，
支持 Filecore、ICS-IDE、EESOX、PowerTec 与 PC/BIOS 分区格式。

## 功能概述

- 编辑 Acorn 机器上的磁盘分区表
- 自动检测分区方案（Filecore / ICS IDEFS / PowerTec / PC-BIOS）
- 交互式命令行前端，反馈操作结果

## OHOS 适配

- **纯 Makefile 构建**：上游无 configure 脚本，顶层 Makefile 直接编译 fdisk
  及各静态库（lib/part.a lib/scheme.a lib/blkio.a lib/util.a）
- **编译器**：通过 Conan `tools.build:compiler_executables` 传入 OHOS clang，
  不依赖 shell 环境变量（R33）
- **STRIP/LDFLAGS 覆盖**：顶层 Makefile 默认 `STRIP=strip`、`LDFLAGS=-N`，
  在 OHOS 上不适用，构建时覆盖为 `STRIP=: LDFLAGS=""`
- **许可证**：上游 tarball 不含 COPYING，依据 Debian packaging copyright 声明 GPL-1+
- **二进制命名**：上游产物为 `fdisk`，按 Debian 惯例安装为 `bin/acorn-fdisk`
- **无上游测试**：Makefile 仅定义 all/clean/tar 目标；消费者测试通过
  test_package 执行 `--version`、`--help` 与坏设备路径验证

## 使用方法

```bash
acorn-fdisk --version
acorn-fdisk --help
acorn-fdisk /dev/sda
```
