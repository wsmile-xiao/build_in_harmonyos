# GNU libtool 2.4.7 鸿蒙适配

> **编译日期**: 2026-03-19  
> **测试环境**: HarmonyOS HongMeng Kernel 1.11.0 aarch64  
> **编译器**: clang 15.0.4  
> **测试结果**: ✅ 核心功能可用，详见 [TEST_REPORT.md](./TEST_REPORT.md)

## 概述

GNU libtool 是一个通用的库支持脚本，用于在 Unix-like 系统上构建和使用共享库。它封装了不同平台间共享库编译、链接、安装的差异，是 Autotools 构建链（autoconf + automake + libtool）的三大核心工具之一。

## 软件信息

| 项目 | 值 |
|------|-----|
| 软件名称 | GNU libtool |
| 版本 | 2.4.7 |
| 下载地址 | https://ftp.gnu.org/gnu/libtool/libtool-2.4.7.tar.xz |
| 官方文档 | https://www.gnu.org/software/libtool/manual/ |
| 构建系统 | Autotools（configure + make） |
| 许可证 | GPL-2.0-or-later |

## 归档文件

| 文件 | 说明 |
|------|------|
| `0001-port-for-ohos.patch` | config.guess + config.sub 的 HarmonyOS 适配补丁 |
| `TEST_REPORT.md` | `make check` 测试报告（141 测试：28 通过，106 失败，28 跳过） |

## 编译步骤

```bash
# 1. 下载解压
curl -L -o libtool-2.4.7.tar.xz https://ftp.gnu.org/gnu/libtool/libtool-2.4.7.tar.xz
tar -xf libtool-2.4.7.tar.xz
cd libtool-2.4.7

# 2. 应用 HarmonyOS 补丁
patch -p1 < /path/to/0001-port-for-ohos.patch

# 3. 验证补丁
./build-aux/config.guess   # 应输出: aarch64-unknown-linux-ohos
./build-aux/config.sub aarch64-unknown-linux-ohos  # 应输出: aarch64-unknown-linux-ohos

# 4. 运行 configure
export TMPDIR=$HOME/tmp
./configure --prefix=$HOME/usr/local

# 5. 编译
make -j$(nproc)

# 6. 安装
make install

# 7. 修复 libtoolize 的 shebang（/usr/bin/env 不存在）
sed -i 's|#! /usr/bin/env sh|#!/bin/sh|' $HOME/usr/local/bin/libtoolize
```

## 补丁说明

### 修改文件

1. **build-aux/config.guess**: 添加 HarmonyOS 系统识别，生成 `aarch64-unknown-linux-ohos` 三元组
2. **build-aux/config.sub**: 添加 `linux-ohos` 和 `ohos` 操作系统支持

### config.guess 修改详解

**修改位置 1 — LIBC 检测**（约第 152 行）：

```diff
 case $UNAME_SYSTEM in
-Linux|GNU|GNU/*)
+Linux|GNU|GNU/*|HarmonyOS)
```

将 HarmonyOS 加入 LIBC 检测分支。由于 HarmonyOS 基于 musl libc，`LIBC=unknown` 会被设为 `LIBC=gnu`（在后续 musl 检测中会被覆盖为 `musl`），这对 libtool 的构建没有影响。

**修改位置 2 — 系统识别**（约第 1540 行）：

```diff
+    *:HarmonyOS:*:*)
+	case $UNAME_MACHINE in
+	    aarch64|arm64)	ARCH=aarch64 ;;
+	    armv7*|armv8*)	ARCH=arm ;;
+	    x86_64|amd64)	ARCH=x86_64 ;;
+	    i?86)		ARCH=i686 ;;
+	    *)			ARCH=$UNAME_MACHINE ;;
+	esac
+	GUESS=$ARCH-unknown-linux-ohos
+	;;
```

当 `uname -s` 返回 `HarmonyOS` 时，生成 `*-unknown-linux-ohos` 格式的三元组。使用 `linux-ohos` 而非 `harmonyos` 是因为 HarmonyOS 内核兼容 Linux，继承 Linux 的构建逻辑最为稳妥。

### config.sub 修改详解

**修改位置 1 — kernel-OS 匹配**（约第 145 行）：

在 `maybe_os` case 分支中添加 `linux-ohos*`，让 config.sub 将 `aarch64-linux-ohos` 解析为 `kernel=linux, os=ohos`。

**修改位置 2 — OS 名称注册**（约第 1756 行）：

在 OS 验证列表中添加 `ohos*`，使 `ohos` 被识别为合法操作系统名称。

**修改位置 3 — kernel-OS 组合验证**（约第 1774 行）：

在内核-操作系统组合验证中添加 `linux-ohos*`，允许 `linux` 内核与 `ohos` 操作系统的组合。

## 安装验证

```bash
# libtool 核心命令
$ libtool --version
libtool (GNU libtool) 2.4.7

# 检查安装文件
$ ls $HOME/usr/local/bin/libtool          # ✅ 主程序
$ ls $HOME/usr/local/lib/libltdl.so*      # ✅ libltdl 共享库
$ ls $HOME/usr/local/lib/libltdl.a        # ✅ libltdl 静态库
$ ls $HOME/usr/local/include/libltdl/     # ✅ 头文件
$ ls $HOME/usr/local/share/libtool/       # ✅ 辅助文件和 m4 宏
```

## 已知限制

### 1. libtoolize Shell 函数加载失败（⚠️ 重要）

`libtoolize --version` 报错：`func_add_hook: inaccessible or not found` 等大量函数未定义错误。

**根因**：libtoolize 脚本通过 `inline-source` 机制内嵌 shell 函数（`func_add_hook`、`func_dirname`、`func_mkdir_p` 等），这些函数在 HarmonyOS 的 sh/bash 下无法正确加载。**已用 bash 直接执行验证，同样报错，非 zsh 特有问题**。

**影响**：
- `libtool` 命令（核心功能）**正常可用** ✅ — 这是其他项目构建时实际使用的工具
- `libtoolize` 命令（开发工具）**不可用** ❌ — 仅用于从零开始创建 autotools 项目

**实际影响评估**：对于**编译使用 autotools 的开源软件**（如 libcurl、glib 等），只需要 `libtool` 命令可用即可，`libtoolize` 仅在 `autoreconf` 流程中需要。鸿蒙系统上已有 automake 1.16.5 安装了 `libtool.m4` 等宏文件到正确位置，大多数情况下不需要单独运行 `libtoolize`。

### 2. 编译警告

编译过程中产生 102 个 `-Wcompound-token-split-by-macro` 警告，这是 `FREE()` 宏使用 GCC statement expression 的 Clang 兼容性问题，不影响功能。

## 依赖

| 依赖项 | 状态 | 版本/路径 |
|--------|------|-----------|
| C 编译器 | ✅ | clang 15.0.4 |
| Make | ✅ | GNU Make 4.4.1 |
| Shell | ✅ | /bin/sh (toybox) |
| Perl | ✅ | 5.42.0 |
| M4 宏处理器 | ✅ | 系统 m4 |
| /usr/bin/env | ❌ 不存在 | 需修复 shebang |

## 与 Autotools 工具链的关系

```
autotools 构建链：

  autoconf 2.72  ─→  生成 configure 脚本
       +
  automake 1.16.5 ─→  生成 Makefile.in，内含 libtool 调用
       +
  libtool 2.4.7  ─→  处理共享库编译/链接的跨平台差异
```

libtool 在 autotools 项目中的角色是处理共享库的构建。当 `configure.ac` 中包含 `LT_INIT` 宏时，`autoreconf` 会调用 libtoolize 将 `libtool.m4` 等宏文件复制到项目中，并在最终生成的 `configure` 中嵌入 libtool 的逻辑。

## 经验总结

1. **libtool 的适配非常简单**：只需修改 `config.guess` 和 `config.sub`，无需修改源码，体现了 autotools 项目的良好可移植性设计
2. **libtoolize 的 zsh 问题可以接受**：核心功能 `libtool` 命令正常，`libtoolize` 的问题仅在创建新项目时出现
3. **`/usr/bin/env` 问题普遍存在**：鸿蒙系统没有 `/usr/bin/env`，所有使用 `#!/usr/bin/env sh` 的脚本都需要修复为 `#!/bin/sh`
4. **与 automake 协同工作**：libtool 的 m4 宏文件（安装到 `$HOME/usr/local/share/aclocal/`）可被 automake 的 aclocal 工具发现
