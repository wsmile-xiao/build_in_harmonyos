# ncurses 6.4 鸿蒙系统编译指南

## 概述

本文档记录了 ncurses 6.4 在鸿蒙系统上的编译适配过程，包括遇到的问题、解决方案和注意事项。

## 软件信息

- **软件名称**: ncurses
- **版本**: 6.4
- **构建系统**: Autotools (configure)
- **下载地址**: https://ftp.gnu.org/gnu/ncurses/ncurses-6.4.tar.gz

## 鸿蒙环境

- **系统**: HarmonyOS
- **内核**: HongMeng Kernel
- **架构**: aarch64
- **编译器**: Clang 15.0.4
- **工具链**: LLVM (llvm-ar, llvm-ranlib, llvm-nm, llvm-strip)

## 编译步骤

### 1. 解压源码

```bash
tar -xzf ncurses-6.4.tar.gz
cd ncurses-6.4
```

### 2. 应用补丁

```bash
patch -p1 < 0001-port-for-ohos.patch
```

### 3. 配置

```bash
export TMPDIR=$HOME/tmp
export PATH="$HOME/usr/local/bin:$PATH"  # 确保使用 GNU 工具
./configure --prefix=$HOME/usr/local \
    --with-shared \
    --enable-widec
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

1. **config.guess**: 添加 HarmonyOS 系统检测
2. **config.sub**: 添加 `linux-ohos` 三元组支持

### 关键修改详解

#### 1. config.guess - HarmonyOS 系统识别

**问题背景**: GNU config 的 config.guess 不识别 HarmonyOS 系统，导致 configure 无法正确识别目标平台。

**技术原理**:
```
uname -s 在不同系统上的输出:
- Linux: "Linux"
- HarmonyOS: "HarmonyOS"
```

**解决方案**: 在 Linux 检测之前添加 HarmonyOS 检测：

```bash
*:HarmonyOS:*:*)
    case "$UNAME_MACHINE" in
        aarch64|arm64)
            MACHINE=aarch64
            ;;
        armv7*|armv8*)
            MACHINE=arm
            ;;
        x86_64|amd64)
            MACHINE=x86_64
            ;;
        i?86)
            MACHINE=i686
            ;;
        *)
            MACHINE="$UNAME_MACHINE"
            ;;
    esac
    GUESS=${MACHINE}-unknown-linux-ohos
    ;;
```

**修改位置**: 在 `*:Linux:*:*)` 检测之前

**目标三元组说明**:
- 格式: `cpu-vendor-kernel-os`
- HarmonyOS: `aarch64-unknown-linux-ohos`
- `linux-ohos` 表示使用 Linux 内核 API 但运行在 HarmonyOS 上

#### 2. config.sub - 操作系统验证

**问题背景**: config.sub 用于验证目标三元组的合法性，需要添加 `ohos` 作为有效的操作系统标识。

**修改内容**:

1. 在有效操作系统列表中添加 `ohos*`：
```bash
# 原始
-linux* | -kfreebsd* | ...
# 修改后
-linux* | -ohos* | -kfreebsd* | ...
```

2. 在内核-操作系统验证中添加 `linux-ohos*`：
```bash
-linux-gnu* | -linux-musl* | ...
# 添加
-linux-ohos*
```

**技术说明**: 
- `ohos` 作为操作系统后缀，与 `gnu`、`musl` 并列
- 表示使用 HarmonyOS 的用户空间和 API

## 遇到的问题

### 问题 1: toybox expr 复合正则表达式 Bug（根本原因）

**现象**: 
- config.status 执行时，子目录 Makefile 中的 `top_srcdir` 被错误设置为乱码
- 乱码模式有规律，像是内存数据被错误输出

**排查过程**:
```bash
# 追踪 config.status 执行
bash -x ./config.status --file=ncurses/Makefile 2>&1 | grep ac_dir

# 发现变量值异常
+ ac_dots='../<乱码>...'
```

**根本原因**:
- 鸿蒙默认使用 **toybox expr**
- toybox expr 在处理**复合正则表达式**（使用 `\|` 操作符）时存在严重 bug
- autoconf 的 config.status 使用复杂的 expr 命令来提取路径组件

**问题复现**:
```bash
# toybox expr (错误)
$ expr X"ncurses/Makefile" : 'X\(.*[^/]\)//*[^/][^/]*/*$' \| . : '\(.\)'
mOkk...  # 输出乱码

# GNU expr (正确)
$ expr X"ncurses/Makefile" : 'X\(.*[^/]\)//*[^/][^/]*/*$' \| . : '\(.\)'
ncurses  # 正确输出
```

**技术分析**:
```
config.status 中的 expr 命令链:
expr X"$ac_file" : 'X\(.*[^/]\)//*[^/][^/]*/*$' \
  \| X"$ac_file" : 'X\(//\)[^/]' \
  \| X"$ac_file" : 'X\(//\)$' \
  \| X"$ac_file" : 'X\(/\)' \
  \| . : '\(.\)'

这个命令链用于从路径中提取目录部分：
- 输入: "ncurses/Makefile"
- 预期输出: "ncurses"
- toybox 输出: 乱码（复合正则表达式处理 bug）
```

**解决方案**: 
- 编译安装 **GNU coreutils**（包含正确的 GNU expr）
- 设置 PATH 优先使用 GNU 工具

```bash
# 编译 GNU coreutils
cd /path/to/coreutils-9.10
./configure --prefix=$HOME/usr/local --disable-nls
make
cp src/expr $HOME/usr/local/bin/

# 设置 PATH
export PATH="$HOME/usr/local/bin:$PATH"
```

### 问题 2: 临时目录不可写

**现象**: configure 过程中无法创建临时文件

**解决方案**: 设置 `TMPDIR` 环境变量

```bash
export TMPDIR=$HOME/tmp
mkdir -p $TMPDIR
```

## 经验总结

### HarmonyOS 工具链差异

| 方面 | Linux | HarmonyOS |
|------|-------|-----------|
| expr | GNU expr | toybox expr (复合正则有 bug) |
| sed | GNU sed | toybox sed / GNU sed |
| awk | gawk/mawk | toybox awk |
| shell | bash | mksh/sh |
| 临时目录 | /tmp 可写 | 需要设置 TMPDIR |

### 关键发现

1. **toybox expr 的 bug 是隐蔽的**:
   - 简单的正则表达式工作正常
   - 复合正则表达式（`\|` 操作符）输出乱码
   - 这导致 autotools 项目生成的 Makefile 出现问题

2. **需要安装的关键 GNU 工具**:
   - **GNU coreutils** (expr 是最关键的)
   - **GNU sed** (用于复杂脚本)

3. **PATH 优先级非常重要**:
   ```bash
   export PATH="$HOME/usr/local/bin:$PATH"
   ```

### 注意事项

1. **先安装 GNU coreutils**: 在编译其他 autotools 项目前，先安装 GNU coreutils

2. **环境变量设置**:
   ```bash
   export TMPDIR=$HOME/tmp
   export PATH="$HOME/usr/local/bin:$PATH"
   ```

3. **编译顺序建议**:
   - GNU coreutils (提供 expr)
   - GNU sed
   - 其他 autotools 项目 (如 ncurses)

## 相关项目

- **GNU coreutils**: 提供 GNU expr，解决 toybox expr bug
- **GNU sed**: 替代 toybox sed，完整支持复杂脚本

## 编译产物

编译成功后生成以下库文件：

- libncursesw.so.6.4 - 主库（宽字符版本）
- libformw.so.6.4 - 表单库
- libmenuw.so.6.4 - 菜单库
- libpanelw.so.6.4 - 面板库
- libncurses++w.a - C++ 绑定（静态库）

## 参考资料

- ncurses 官方文档: https://invisible-island.net/ncurses/
- GNU config: https://git.savannah.gnu.org/cgit/config.git/
- GNU coreutils 鸿蒙适配: build_in_harmonyos/c/coreutils/9.9/README.md
- 鸿蒙编译知识库: build_in_harmonyos/SKILL.md

## 版本历史

- 2026-03-15: 更新问题分析，明确 toybox expr bug 为根本原因
- 2026-03-14: 初始版本，完成 ncurses 6.4 鸿蒙适配