# pimd 2.3.2 适配笔记

## 编译环境
- 构建系统: 手写 `configure`（生成 `config.mk`）+ 顶层 `Makefile`（非 autoconf）
- 编译日期: 2026-10-03
- 编译器: OHOS SDK clang（Conan profile 的 `tools.build:compiler_executables.c`）
- 状态: built

## 编译步骤

1. 取 Debian orig 源码包 `pimd_2.3.2.orig.tar.gz`（含自带 libite 子目录）。
2. `build()` 先 `sh ./configure`（补丁已加 HarmonyOS 分支、并把临时文件改到构建目录），
   再 `make CC=<ohos clang> -j1`，产出 `pimd`。
3. `package()` 安装 `bin/pimd`、`share/man/man8/pimd.8`、`share/pimd/pimd.conf`、
   `licenses/{LICENSE*,AUTHORS,README.md}`。
4. `test_package/test_pimd.sh` 运行 6 项检查。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `./configure` 报 `HarmonyOS is currently unsupported` | 手写 configure 的 `case $OS` 只列 Linux/FreeBSD/NetBSD/OpenBSD | 补丁把 `Linux)` 改成 `Linux|HarmonyOS)`，复用 Linux 的 DEFS/EXTRA_OBJS/ROUTER_OBJS |
| 2 | `mktemp: Failed to create file /tmp/XXXXXX: Read-only file system` | OHOS `/tmp` 只读，configure 写临时文件失败（后续 `can't create`） | 补丁把 `mktemp /tmp/XXXXXX` 改成 `mktemp config.mk.XXXXXX`（在构建目录建） |
| 3 | `-lutil` 等平台库 | Linux 分支 `EXTRA_LIBS =` 为空，无需额外库 | 沿用 Linux 设置即可 |

## 源码修改

| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|----------|
| `configure` | 不支持 HarmonyOS、临时文件写到只读 /tmp | `Linux\|HarmonyOS` 分支 + `mktemp config.mk.XXXXXX` | ✅ `patches/0001-ohos-support.patch` |

## 依赖版本

无三方依赖（自带 libite 的 4 个对象直接编译进 `pimd`）。

## 验证结果

```bash
# 消费者（test_package/test_pimd.sh，6 项）
PIMD_CHECK_SUMMARY checks=6 fails=0
```

## 注意事项

- 上游无测试套件，按 §3.6 口径声明上游 N=0，另加鸿蒙特有（消费者）测试 6 项。
- 功能级运行需要组播网卡与 root，消费者测试只覆盖 `-v/--version/--help`。
