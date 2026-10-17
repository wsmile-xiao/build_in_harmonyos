# kernel-hardening-checker

**A tool for checking the security hardening options of the Linux kernel**

## 简介

kernel-hardening-checker 用于检查 Linux 内核的安全加固选项：Kconfig 配置
（`-c`）、内核命令行（`-l`）、sysctl 输出（`-s`），并可输出各架构的加固建议
（`-p`）或生成 Kconfig 加固片段（`-g`）。纯 Python 实现（GPL-3.0-only），
仅依赖标准库，无需编译 C/C++ 代码。

## 特性

- 检查 Kconfig 加固选项（支持 `.config` 与 gzip 压缩格式）
- 检查内核命令行参数与 sysctl 输出的加固状态
- 支持 X86_64/X86_32/ARM64/ARM/RISCV 五种架构的规则集
- `-p` 打印架构加固建议，`-g` 生成 Kconfig 加固片段
- 附带约 90 个真实内核配置样例（config_files/：defconfigs、distros、
  KSPP 建议）

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.6.17.1 | ✅ 已适配 | 纯 Python CLI，对应 Linux v6.17 规则集 |

## 上游信息

- **官方仓库**: https://github.com/a13xp0p0v/kernel-hardening-checker
- **许可证**: GPL-3.0-only
- **语言**: Python 3（>= 3.9）

## 使用方式

```bash
# 查看版本
kernel-hardening-checker --version

# 打印 ARM64 加固建议
kernel-hardening-checker -p ARM64

# 生成 ARM64 Kconfig 加固片段
kernel-hardening-checker -g ARM64

# 检查一个内核配置文件（支持 .gz）
kernel-hardening-checker -c /path/to/kernel.config
```

## 依赖

- Python 3（>= 3.9，纯标准库，无第三方运行时依赖）
- setuptools >= 77.0.3（仅构建时）

## 适配说明

HarmonyOS aarch64 上为纯 Python 无编译打包（pip staging 安装 +
便携 `/bin/sh` wrapper）。上游代码无平台分支、无 patch：

- 包内无 `__main__.py`，wrapper 通过 `import kernel_hardening_checker` 后
  直接调用 `main()`（与上游 `bin/kernel-hardening-checker` 免安装 launcher
  同款方式）；
- recipe 从源码防御式补拷 `config_files/` 样例树（实测上游 wheel 已含
  全部 94 个样例文件，补拷仅作保险），`-c <官方示例 .config>` 开箱可用；
- `-a` autodetect 依赖 `/proc/config.gz`、`/boot`、`/proc/cmdline`，
  OHOS 设备不提供这些接口，该模式在设备上不可用（预期行为）；
  `-c/-p/-g/-s` 等基于用户输入文件的模式均可用。

## 维护者

AtomCode AI
