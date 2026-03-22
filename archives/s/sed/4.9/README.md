# GNU sed 4.9 鸿蒙系统编译指南

## 概述

本文档记录了 GNU sed 4.9 在鸿蒙系统上的编译适配过程。GNU sed 是一个功能强大的流编辑器，支持复杂的脚本功能，包括分支命令、标签等高级特性。

## 软件信息

- **软件名称**: GNU sed
- **版本**: 4.9
- **构建系统**: Autotools (configure)
- **下载地址**: https://ftp.gnu.org/gnu/sed/sed-4.9.tar.gz

## 鸿蒙环境

- **系统**: HarmonyOS
- **内核**: HongMeng Kernel
- **架构**: aarch64
- **编译器**: Clang 15.0.4
- **工具链**: LLVM (llvm-ar, llvm-ranlib, llvm-nm, llvm-strip)

## 编译步骤

### 1. 下载并解压源码

```bash
curl -L -o sed-4.9.tar.gz https://ftp.gnu.org/gnu/sed/sed-4.9.tar.gz
tar -xzf sed-4.9.tar.gz
cd sed-4.9
```

### 2. 应用补丁

```bash
patch -p1 < 0001-port-for-ohos.patch
```

### 3. 配置

```bash
export TMPDIR=$HOME/tmp
mkdir -p $TMPDIR
./configure --prefix=$HOME/usr/local
```

### 4. 编译

```bash
make
```

### 5. 安装

```bash
make install
```

## 补丁说明

### 修改文件

1. **build-aux/config.guess**: 添加 HarmonyOS 系统检测
2. **build-aux/config.sub**: 添加 `linux-ohos` 三元组支持

### 关键修改详解

#### 1. config.guess - HarmonyOS 系统识别

**问题背景**: GNU config 的 config.guess 不识别 HarmonyOS 系统，导致 configure 无法正确识别目标平台。

**技术原理**:
```
uname -s 在不同系统上的输出:
- Linux: "Linux"
- HarmonyOS: "HarmonyOS"
```

**解决方案**: 在适当位置添加 HarmonyOS 检测：

```bash
*:HarmonyOS:*:*)
    case "$UNAME_MACHINE" in
        aarch64|arm64)
            GUESS=aarch64-unknown-linux-ohos
            ;;
        x86_64|amd64)
            GUESS=x86_64-unknown-linux-ohos
            ;;
        *)
            GUESS=$UNAME_MACHINE-unknown-linux-ohos
            ;;
    esac
    ;;
```

**修改位置**: 在 `*:Linux:*:*)` 检测之前或之后

**目标三元组说明**:
- 格式: `cpu-vendor-kernel-os`
- HarmonyOS: `aarch64-unknown-linux-ohos`
- `linux-ohos` 表示使用 Linux 内核 API 但运行在 HarmonyOS 上

#### 2. config.sub - 操作系统验证

**问题背景**: config.sub 用于验证目标三元组的合法性，需要添加 `ohos` 作为有效的操作系统标识。

**修改内容**:

1. 在有效操作系统列表中添加 `ohos*`
2. 在内核-操作系统验证中添加 `linux-ohos*`

**技术说明**: 
- `ohos` 作为操作系统后缀，与 `gnu`、`musl` 并列
- 表示使用 HarmonyOS 的用户空间和 API

## 为什么需要 GNU sed？

### 功能对比

鸿蒙系统默认使用 toybox sed，存在以下限制：

| 功能 | toybox sed | GNU sed |
|------|------------|---------|
| 基本替换 `s/pattern/replacement/` | ✓ 支持 | ✓ 支持 |
| 多行命令块 `{...}` | ⚠️ 可能异常 | ✓ 完全支持 |
| 分支命令 `:label` | ⚠️ 可能异常 | ✓ 完全支持 |
| 跳转命令 `b`、`t` | ⚠️ 可能异常 | ✓ 完全支持 |
| 复杂正则表达式 | ⚠️ 功能有限 | ✓ 完全支持 |
| `-z` 处理 NULL 分隔 | ✗ 不支持 | ✓ 支持 |
| 扩展正则 `-E` | ✓ 支持 | ✓ 完全支持 |
| 原地编辑 `-i` | ✓ 支持 | ✓ 完全支持 |
| 保持空间 `h/H/g/G/x` | ⚠️ 可能异常 | ✓ 完全支持 |

### autotools 兼容性

autotools 生成的 configure 脚本可能使用复杂的 sed 命令：

```bash
# 典型的 autotools sed 用法
sed -n '/^[^#]/p' config.h.in | while read line; do
    # 复杂的多行处理
done

# 带分支的 sed 脚本
sed ':a;N;$!ba;s/\n/ /g' file.txt
```

这些复杂用法在 toybox sed 上可能出现问题，使用 GNU sed 更可靠。

## 功能验证

### 1. 版本检查

```bash
$ $HOME/usr/local/bin/sed --version
sed (GNU sed) 4.9
Copyright (C) 2022 Free Software Foundation, Inc.
```

### 2. 基本功能

```bash
$ echo "hello world" | sed 's/world/GNU sed/'
hello GNU sed
```

### 3. 复杂脚本（分支命令）

```bash
# 循环打印所有行
$ echo -e "line1\nline2\nline3" | sed -n ':a;p;n;ba'
line1
line2
line3

# 条件替换
$ echo -e "start\nmiddle\nend" | sed '/start/,/end/s/middle/MIDDLE/'
start
MIDDLE
end
```

### 4. 保持空间操作

```bash
# 交换行
$ echo -e "first\nsecond" | sed -n 'h;n;G;p'
second
first
```

## 设置默认使用 GNU sed

将 GNU sed 路径添加到 PATH 前面：

```bash
export PATH=$HOME/usr/local/bin:$PATH
```

或在脚本中显式使用：

```bash
#!/bin/bash
SED=$HOME/usr/local/bin/sed
$SED 's/pattern/replacement/g' file.txt
```

## 注意事项

1. **临时目录**: 配置前确保设置 `TMPDIR=$HOME/tmp`

2. **依赖**: GNU sed 可能依赖以下库：
   - gettext
   - libintl
   - libregex

3. **路径**: 安装后确保将 `$HOME/usr/local/bin` 添加到 PATH

4. **编译顺序**: 建议在编译其他 autotools 项目前先安装 GNU sed

## 相关项目

- **GNU coreutils**: 提供 GNU expr 等核心工具
- **ncurses**: 终端库，需要正确的 autotools 环境

## 参考资料

- GNU sed 官方文档: https://www.gnu.org/software/sed/manual/
- GNU sed 下载: https://ftp.gnu.org/gnu/sed/
- GNU config: https://git.savannah.gnu.org/cgit/config.git/
- 鸿蒙编译知识库: build_in_harmonyos/SKILL.md

## 版本历史

- 2026-03-15: 补充补丁说明的详细技术解释
- 2026-03-14: 初始版本，完成 GNU sed 4.9 鸿蒙适配