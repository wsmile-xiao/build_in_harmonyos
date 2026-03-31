# build_in_harmonyos

> 在 HarmonyOS PC 上从源码编译开源软件的知识库与编译档案

## 项目简介

本项目旨在解决一个核心问题：**开源软件无法直接在鸿蒙 PC 上编译运行**。

鸿蒙系统与主流 Linux 发行版存在根本性差异——musl libc 替代 glibc、clang 替代 gcc、SELinux 强制策略限制软链接和子进程、toybox 替代 GNU coreutils——导致绝大多数开源软件的构建系统无法正确识别平台或编译失败。

我们通过逐个编译开源软件，沉淀出了一套**可复用的适配方法论和知识体系**，让后续软件的编译不再从零开始。

## 项目定位

```
知识不遗漏 → 档案结构化 → 检索高效化 → 复用精准化
```

| 维度 | 说明 |
|------|------|
| **知识库** | 19 篇文档覆盖环境特性、构建系统适配、错误模式、打包发布等全流程 |
| **编译档案** | 26 款软件、29 个版本的完整编译记录，含补丁、配置和测试报告 |
| **经验沉淀** | 44 个已编目的错误模式，覆盖配置、编译、链接、运行时各阶段 |

## 编译成果

### 已完成编译（26 款 / 29 版本）

| 软件 | 版本 | 状态 | 构建系统 | 说明 |
|------|------|------|----------|------|
| Python | 3.9.0 / 3.9.25 / 3.12.9 | ⚠️ 部分成功 | Autotools | 3.9.0: 84 补丁；3.9.25: 82 补丁（已测试）；3.12.9: 26 补丁 |
| OpenSSL | 1.1.1w | ✅ 成功 | Custom-Perl | 需 `no-asm`，提供 `python-3.9.0` SSL 支持 |
| ncurses | 6.4 | ✅ 成功 | Autotools | Python curses 模块依赖 |
| readline | 8.2 | ✅ 成功 | Autotools | Python readline 模块依赖 |
| gdbm | 1.23 | ✅ 成功 | Autotools | Python dbm/gdbm 模块依赖 |
| zlib | 1.3.1 | ✅ 成功 | CMake | Python zlib 模块依赖 |
| bzip2 | 1.0.8 | ✅ 成功 | Makefile | Python bz2 模块依赖 |
| libffi | 3.4.4 / 3.5.2 | ✅ 成功 | Autotools | Python ctypes 模块依赖 |
| coreutils | 9.10 | ⚠️ 部分成功 | Autotools | 核心 utils 可用，部分功能受限 |
| bash | 5.3 | ✅ 成功 | Autotools | 需 `--without-bash-malloc` |
| gawk | 5.3.0 | ✅ 成功 | Autotools | 需 `-D_GNU_SOURCE` |
| sed | 4.9 | ✅ 成功 | Autotools | 替代 toybox sed |
| tar | 1.35 | ✅ 成功 | Autotools | |
| make (GNU) | 4.4.1 | ✅ 系统自带 | Autotools | |
| cmake | 4.1.2 | ✅ 系统自带 | CMake | |
| autoconf | 2.72 | ✅ 系统自带 | Autotools | |
| libtool | 2.4.7 | ✅ 成功 | Autotools | |
| automake | 1.16.5 | ✅ 成功 | Autotools | |
| libpipeline | 1.5.8 | ✅ 成功 | Autotools | man-db 依赖 |
| man-db | 2.13.1 | ✅ 成功 | Autotools | |
| help2man | 1.49.3 | ✅ 成功 | Script | |
| patch | 2.7.6 | ⚠️ 部分成功 | Autotools | |
| htop | 3.4.1 | ⚠️ 部分成功 | Autotools | 需 sudo 运行 |
| jq | 1.7.1 | ✅ 成功 | Autotools | |
| rsync | 3.3.0 | ⚠️ 部分成功 | Autotools | |
| strace | 6.19 | ⚠️ 部分成功 | Autotools | ptrace 被 SELinux 禁止 |
| wget | 1.19.1 | ⚠️ 部分成功 | Autotools | HTTPS 需跳过证书验证 |

> **状态说明**：✅ 成功 = 核心功能正常可用 | ⚠️ 部分成功 = 核心功能可用，部分功能受鸿蒙限制 | ❌ 失败

### 依赖关系

```
Python 3.9.0
├── OpenSSL 1.1.1w
│   └── (无外部依赖)
├── ncurses 6.4
├── readline 8.2
├── gdbm 1.23
├── zlib 1.3.1
├── bzip2 1.0.8
├── libffi 3.4.4
└── xz 5.6.2
```

## 知识库

本项目积累了 19 篇系统性知识文档，覆盖鸿蒙平台适配的各个方面：

### 核心文档

| 文档 | 内容 | 何时查阅 |
|------|------|----------|
| [environment.md](knowledge/environment.md) | 环境变量、工具链、DevBox/HiShell、系统限制 | 编译前必读 |
| [harmonyos-specifics.md](knowledge/harmonyos-specifics.md) | ELF 签名机制、SELinux 域转换、软链接限制、HiShell 兼容性 | 遇到平台特有问题时 |
| [build-systems.md](knowledge/build-systems.md) | Autotools/CMake/Custom-Perl 构建系统适配策略 | 开始适配新软件时 |
| [error-patterns.md](knowledge/error-patterns.md) | 44 个已编目的错误模式（E001-E044）及解决方案 | 遇到编译错误时 |
| [packaging.md](knowledge/packaging.md) | 可移植打包：RPATH、strip、debug 分离、ELF 签名流程 | 制作发布包时 |

### 专题文档

| 文档 | 内容 |
|------|------|
| [musl-compat.md](knowledge/musl-compat.md) | musl 与 glibc 的差异及兼容方案 |
| [musl-glibc-developer-impact.md](knowledge/musl-glibc-developer-impact.md) | musl 对开发者的实际影响评估 |
| [python-extensions.md](knowledge/python-extensions.md) | Python C 扩展模块编译方法（含 HMDFS 符号链接修复） |
| [dependencies.md](knowledge/dependencies.md) | 编译依赖关系与推荐编译顺序 |
| [autotools-patterns.md](knowledge/autotools-patterns.md) | Autotools 项目适配模式 |
| [best-practices.md](knowledge/best-practices.md) | 编译最佳实践与经验总结 |
| [troubleshooting.md](knowledge/troubleshooting.md) | 问题排查指南 |
| [FAQ.md](knowledge/FAQ.md) | 常见问题解答 |

### 深度分析

| 文档 | 内容 |
|------|------|
| [filesystem-analysis.md](knowledge/filesystem-analysis.md) | HMFS/HMDFS/EROFS 文件系统架构分析 |
| [filesystem-impact-assessment.md](knowledge/filesystem-impact-assessment.md) | 文件系统差异对各用户画像的影响评估 |
| [ptrace-alternatives.md](knowledge/ptrace-alternatives.md) | ptrace 不可用时的调试替代方案 |
| [sudo-analysis.md](knowledge/sudo-analysis.md) | 鸿蒙 sudo 功能分析 |

## 项目结构

```
build_in_harmonyos/
├── README.md                    # 本文档
├── CHANGELOG.md                 # 变更日志
├── CONTRIBUTING.md              # 贡献指南
├── MISSING_TOOLS.md             # 缺失工具清单
├── SKILL.md                     # AI 编译智能体技能定义
│
├── knowledge/                   # 知识库（19 篇文档）
│   ├── environment.md           # 环境特性与配置
│   ├── harmonyos-specifics.md   # 鸿蒙特有机制
│   ├── build-systems.md         # 构建系统适配
│   ├── error-patterns.md        # 错误模式库（44 个）
│   ├── packaging.md             # 可移植打包指南
│   └── ...                      # 更多文档
│
├── archives/                    # 编译档案（26 款软件）
│   ├── _index.yaml              # 软件索引
│   ├── p/python/3.9.0/          # 示例：Python 完整档案
│   │   ├── manifest.yaml        # 元数据
│   │   ├── README.md            # 编译说明
│   │   ├── patches/             # 10 个适配补丁
│   │   ├── reports/             # 测试报告
│   │   └── scripts/             # 打包脚本
│   └── ...                      # a-z 按首字母组织
│
├── scripts/                     # 辅助脚本
├── templates/                   # 档案模板
└── .opendesk/                   # AI 智能体配置
```

## 目标平台

| 项目 | 值 |
|------|-----|
| 系统 | HarmonyOS (OpenHarmony) |
| 内核 | HongMeng Kernel 1.11.0 |
| 架构 | aarch64 |
| C 库 | musl libc |
| 编译器 | Clang 15.0.4 (LLVM) |
| Shell | HiShell (toybox ash) |
| 终端 | DevBox (VS Code Remote SSH) |

## 鸿蒙平台的主要差异

与标准 Linux 相比，鸿蒙系统在编译层面有以下关键差异：

| 差异点 | Linux | HarmonyOS | 影响 |
|--------|-------|-----------|------|
| C 库 | glibc | musl libc | `BIND_NOW`、`iconv`、`FILE` 结构差异 |
| 编译器 | gcc | clang | 标志、内置宏、警告行为不同 |
| Shell | bash | toybox ash | 不支持 `${BASH_SOURCE}`、数组等 |
| /tmp | 可写 | 只读 | 必须设置 `TMPDIR` |
| SELinux | 通常禁用 | **强制启用** | 软链接、子进程、ptrace 受限 |
| 软链接 | 正常 | 部分受限 | 需 wrapper 脚本替代 |
| ELF 执行 | 无需签名 | **adhoc 签名** | 修改 ELF 后必须重新签名 |
| 并行构建 | `make -j` | **`make -j1`** | FIFO 被 SELinux 禁止 |

## 快速上手

### 环境准备

1. 从**应用市场**安装 **DevBox**（编译工具链）和 **GitNext**（git）
2. 在 HiShell 终端中配置环境变量：

```bash
export DEFAULT_PREFIX=$HOME/usr/local
export CC=clang CXX=clang++
export AR=llvm-ar RANLIB=llvm-ranlib NM=llvm-nm
export CFLAGS="-fPIC -O2"
export TMPDIR=$HOME/tmp
mkdir -p $TMPDIR
```

### 编译软件

1. 选择目标软件，查阅 `archives/` 下是否有现成档案
2. 如有档案，直接复用补丁和配置
3. 如无档案，参考 `knowledge/build-systems.md` 开始适配
4. 编译完成后执行 `make check` 验证
5. 按 `CONTRIBUTING.md` 规范归档

## 相关项目

| 项目 | 说明 |
|------|------|
| [ohos-python-release](https://gitcode.com/OpenHarmonyPCDeveloper/ohos-python-release) | Python 预编译发布包，含安装指南、兼容性报告和构建博客 |

## 许可证

本项目遵循 MIT 许可证。

Copyright (c) 2024-2026 OpenHarmony PC Developer社区
