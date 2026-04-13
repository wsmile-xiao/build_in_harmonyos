# htop 3.4.1 鸿蒙系统编译指南

## 概述

本文档记录了 htop 3.4.1 在鸿蒙系统上的编译适配过程。htop 是一个交互式进程查看器，类似于系统自带的 top 命令，但提供了更丰富的界面和交互功能，支持鼠标操作、树状视图、进程过滤等高级特性。

## 软件信息

- **软件名称**: htop
- **版本**: 3.4.1
- **构建系统**: Autotools (configure)
- **下载地址**: https://github.com/htop-dev/htop/releases/download/3.4.1/htop-3.4.1.tar.xz
- **类别**: 系统监控工具

## 鸿蒙编译环境

- **系统**: HarmonyOS (OpenHarmony)
- **内核**: HongMeng Kernel 1.11.0
- **架构**: aarch64
- **C 库**: musl libc
- **编译器**: Clang 15.0.4 (LLVM)
- **工具链**: LLVM (llvm-ar, llvm-ranlib, llvm-nm, llvm-strip)
- **目标三元组**: aarch64-unknown-linux-ohos
- **安装前缀**: `$HOME/usr/local`

## 编译步骤

### 1. 下载并解压源码

```bash
curl -L -o htop-3.4.1.tar.xz https://github.com/htop-dev/htop/releases/download/3.4.1/htop-3.4.1.tar.xz
tar -xf htop-3.4.1.tar.xz
cd htop-3.4.1
```

### 2. 应用补丁

```bash
patch -p1 < 0001-config-guess-harmonyos.patch
patch -p1 < 0002-config-sub-harmonyos.patch
patch -p1 < 0003-fix-include-path.patch
```

### 3. 配置

```bash
./configure \
    --prefix=$HOME/usr/local \
    LDFLAGS="-static" \
    CFLAGS="-I$HOME/usr/local/include" \
    LIBS="-L$HOME/usr/local/lib -lncursesw"
```

**配置选项说明**：
- `LDFLAGS="-static"`: 静态链接 ncursesw，避免运行时依赖系统的 `libncursesw.so.6`（受鸿蒙 SELinux 限制）
- `CFLAGS="-I$HOME/usr/local/include"`: 指定 ncursesw 头文件路径
- `LIBS="-L$HOME/usr/local/lib -lncursesw"`: 链接本地编译的 ncursesw 静态库

### 4. 编译

```bash
make
```

### 5. 安装

```bash
make install
```

## 补丁说明

共需要 3 个补丁：

### 0001-config-guess-harmonyos.patch

**修改文件**: `config.guess`

**修改内容**:
1. 在 `UNAME_SYSTEM` 的 case 分支中添加 `HarmonyOS` 检测，设置 `LIBC=musl`
2. 在目标三元组输出中添加 `aarch64:HarmonyOS` 的识别，输出 `aarch64-unknown-linux-ohos`

**修改原因**: GNU config 的 config.guess 不识别 HarmonyOS 系统，导致 configure 无法正确识别目标平台。

```diff
+HarmonyOS)
+	LIBC=musl
+	;;
 Linux|GNU|GNU/*)
 	LIBC=unknown

+aarch64:HarmonyOS:*:*)
+	GUESS=aarch64-unknown-linux-ohos
+	;;
 aarch64:Linux:*:*)
```

### 0002-config-sub-harmonyos.patch

**修改文件**: `config.sub`

**修改内容**:
1. 在有效操作系统列表中添加 `ohos*`
2. 在内核-操作系统验证中添加 `linux-ohos*` 和 `ohos*`

**修改原因**: config.sub 用于验证目标三元组的合法性，需要添加 `ohos` 作为有效的操作系统标识。

```diff
-	     | os9* | macos* | osx* | ios* \
+	     | os9* | macos* | osx* | ios* | ohos* \

-		   | linux-musl* | linux-relibc* | linux-uclibc* )
+		   | linux-musl* | linux-relibc* | linux-uclibc* | linux-ohos* | ohos* )
```

### 0003-fix-include-path.patch

**修改文件**: `linux/IOPriorityPanel.h`

**修改内容**: 将 `#include "Panel.h"` 修改为 `#include "../Panel.h"`

**修改原因**: 这是 htop 3.4.1 本身的 bug。`IOPriorityPanel.h` 位于 `linux/` 子目录中，而 `Panel.h` 位于上层目录，直接 `#include "Panel.h"` 无法找到头文件，需要使用相对路径。

```diff
-#include "Panel.h"
+#include "../Panel.h"
```

## 遇到的问题及解决方案

### 问题 1: /proc 文件系统权限限制

**问题描述**: 鸿蒙系统的 SELinux 策略限制了 `/proc` 文件系统的访问权限。普通用户运行 htop 时会报错：

```
Cannot open /proc/stat: Permission denied
```

**解决方案**: 需要使用 `sudo` 权限运行 htop：

```bash
sudo $HOME/usr/local/bin/htop
```

**SELinux 上下文**: `u:object_r:proc_stat_file:s0`

### 问题 2: 系统 libncursesw.so.6 无法加载

**问题描述**: 鸿蒙系统的 `libncursesw.so.6` 也受到 SELinux 限制，普通用户的程序无法加载。

**解决方案**: 使用静态链接 ncursesw 编译 htop，通过 `LDFLAGS="-static"` 实现。

### 问题 3: sudo 后功能键无法工作

**问题描述**: 使用 `sudo` 运行 htop 后，F10（退出）、F9（杀死进程）等功能键无法正常工作。

**原因**: sudo 后 `TERM` 和 `TERMINFO` 环境变量丢失，导致终端功能键映射失效。

**解决方案**: 使用 `sudo -E` 保留环境变量，并显式设置终端信息：

```bash
sudo -E TERM=xterm-256color TERMINFO=$HOME/usr/local/share/terminfo htop
```

## 测试验证结果

htop 没有官方测试套件。核心功能测试需要 sudo 权限：

```bash
# 需要 sudo 权限运行
$ sudo -E TERM=xterm-256color TERMINFO=$HOME/usr/local/share/terminfo $HOME/usr/local/bin/htop
```

功能验证要点：
- 进程列表正常显示
- F1-F10 功能键在正确设置环境变量后可正常工作
- 交互式操作（排序、过滤、树状视图）正常

**状态**: 部分成功（编译安装成功，运行需 sudo 权限）

## 安装产物

| 类型 | 路径 |
|------|------|
| 可执行文件 | `$HOME/usr/local/bin/htop` |

## 依赖说明

编译 htop 3.4.1 需要以下依赖：

- **编译工具**: clang, make
- **终端库**: ncursesw（建议使用本地编译的静态版本）

## 注意事项

1. **必须使用 sudo 运行**: 鸿蒙系统 SELinux 策略限制 `/proc` 文件系统访问
2. **功能键需要保留环境变量**: 使用 `sudo -E` 并设置 `TERM` 和 `TERMINFO`
3. **静态链接 ncursesw**: 避免运行时加载系统共享库失败
4. **状态**: 编译安装完全成功，运行时受限于鸿蒙系统权限策略

## 参考资料

- htop 官方网站: https://htop.dev/
- htop GitHub: https://github.com/htop-dev/htop
- GNU config: https://git.savannah.gnu.org/cgit/config.git/
- 鸿蒙编译知识库: build_in_harmonyos/SKILL.md

## 版本历史

- 2026-03-23: 初始版本，完成 htop 3.4.1 鸿蒙适配（部分成功，需 sudo 运行）
