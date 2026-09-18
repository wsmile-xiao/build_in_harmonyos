# ext4fuse for HarmonyOS (OpenHarmony)

## 概述

ext4fuse 是构建在 FUSE 之上的**只读** EXT4 文件系统实现 (C, 纯 Makefile),
主要用于在非 Linux 系统上读取 Linux ext4 分区。本适配将其 `ext4fuse`
命令行工具带到 HarmonyOS PC (aarch64)。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | ext4fuse |
| 版本 | 0.1.3 (上游最后 tag, 2013) |
| 下载地址 | https://github.com/gerard/ext4fuse/archive/refs/tags/v0.1.3.tar.gz |
| 官方文档 | https://github.com/gerard/ext4fuse |
| 许可证 | GPL-2.0-only |
| 构建系统 | Makefile (`make`, 无 configure / 无 install 目标) |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| SDK | ohos-sdk 26.0.0.18 |
| 架构 | aarch64 |
| 编译器 | clang 15 (LLVM) |
| 依赖 | libfuse/2.9.9 (制品仓已发布), 工具依赖 pkgconf/3.0.6 |

## 已适配版本

- [0.1.3](./0.1.3/)

## 关键适配点

1. **无 install 目标**: 上游 Makefile 只产出 `./ext4fuse` 二进制,
   配方 `package()` 手工 copy 到 `bin/`
2. **pkgconf 命名**: conan 提供的是 `pkgconf` (非 `pkg-config`),
   且生成的 pc 文件不在 conanbuild 的 `PKG_CONFIG_PATH` 上,
   故构建期把 `pkg-config fuse --cflags/--libs` 直接替换为
   libfuse 依赖包的 include/lib 标志 (encfs 1.9.5 同款直取做法)
3. **execinfo.h**: glibc 专属, OHOS bionic 用 `__GLIBC__` 守卫 + no-op stub
4. **FUSE 挂载不可用**: OHOS 无 `/dev/fuse`/mke2fs, 上游 10 个挂载集成测试
   在真机预期 SKIPPED, 可用性由 test_package 二进制 smoke 测试覆盖

## 经验总结

1. 纯 Makefile 配方用 `self.run("make -j1", env="conanbuild")`,
   编译器经 VirtualBuildEnv 注入, 命令行不插值 `$CC` (R33)
2. `package_type = "application"` + 软件级 `commands.json` (R38)
3. 上游测试脚本的 shebang 属 E165 类问题, 构建期指向工具链 bash

## 已知限制

- 只读实现 (上游设计), 仅小端、32 位块号 (上游固有限制)
- OHOS 上无法真实挂载 (无 FUSE 内核模块)
