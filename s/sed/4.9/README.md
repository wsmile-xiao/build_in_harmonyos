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
- **内核**: HongMeng Kernel 1.11.0
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

### 关键修改

与 ncurses-6.4 的修改方式相同，在 config.guess 中添加 HarmonyOS 检测，在 config.sub 中添加 ohos 支持。

## 功能验证

### 1. 版本检查

```bash
$ $HOME/usr/local/bin/sed --version
sed (GNU sed) 4.9
```

### 2. 基本功能

```bash
$ echo "hello world" | sed 's/world/GNU sed/'
hello GNU sed
```

### 3. 复杂脚本（分支命令）

```bash
$ echo -e "line1\nline2\nline3" | sed -n ':a;p;n;ba'
line1
line2
line3
```

## 为什么需要 GNU sed？

鸿蒙系统默认使用 toybox sed，存在以下限制：

| 功能 | toybox sed | GNU sed |
|------|------------|---------|
| 基本替换 | ✓ 支持 | ✓ 支持 |
| 多行命令块 `{...}` | ⚠️ 可能异常 | ✓ 完全支持 |
| 分支命令 `:label` | ⚠️ 可能异常 | ✓ 完全支持 |
| 跳转命令 `b`、`t` | ⚠️ 可能异常 | ✓ 完全支持 |
| 复杂正则表达式 | ⚠️ 功能有限 | ✓ 完全支持 |
| `-z` 处理 NULL 分隔 | ✗ 不支持 | ✓ 支持 |

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
2. **依赖**: GNU sed 依赖 gettext、libintl 等库
3. **路径**: 安装后确保将 `$HOME/usr/local/bin` 添加到 PATH

## 参考资料

- GNU sed 官方文档: https://www.gnu.org/software/sed/manual/
- GNU sed 下载: https://ftp.gnu.org/gnu/sed/
- 鸿蒙编译知识库: build_in_harmonyos/SKILL.md

## 版本历史

- 2026-03-14: 初始版本，完成 GNU sed 4.9 鸿蒙适配