# libedit 20240808 for HarmonyOS

## 概述

libedit 在 HarmonyOS/OpenHarmony (aarch64) 上的编译指南和测试记录。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | libedit |
| 版本 | 20240808 |
| 下载地址 | https://thrysoee.dk/editline/libedit-20240808-3.1.tar.gz |
| 官方文档 | https://thrysoee.dk/editline/ |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS HongMeng Kernel 1.11.0 |
| 架构 | aarch64 |
| 编译器 | clang (LLVM) |
| 构建系统 | autotools |

## 编译步骤

```bash
# 1. 下载源码
wget https://thrysoee.dk/editline/libedit-20240808-3.1.tar.gz
tar -xzf libedit-20240808-3.1.tar.gz
cd libedit-20240808-3.1

# 2. 应用补丁
patch -p1 < patches/0001-aclocal.m4.patch
patch -p1 < patches/0002-compile.patch
patch -p1 < patches/0003-config.guess.patch
patch -p1 < patches/0004-config.sub.patch
patch -p1 < patches/0005-configure.patch
patch -p1 < patches/0006-depcomp.patch
patch -p1 < patches/0007-install-sh.patch
patch -p1 < patches/0008-missing.patch
patch -p1 < patches/0009-termcap.h.patch
patch -p1 < patches/0010-configure-umask.patch

# 3. 配置（仅 --prefix，参数最少化）
./configure --prefix=$HOME/usr/local

# 4. 编译
make -j$(nproc)

# 5. 安装
make install
```

## 补丁说明

### 0001-aclocal.m4.patch
**目的**: 替换 aclocal.m4 为兼容 HarmonyOS 的版本
**修改文件**: `aclocal.m4`

### 0002-compile.patch
**目的**: 修复 compile 脚本的 shebang 和版本兼容性
**修改文件**: `compile`

### 0003-config.guess.patch
**目的**: 添加 HarmonyOS 系统检测
**修改文件**: `config.guess`
**关键修改**: 添加 `__OHOS__` 宏检测和 `HarmonyOS` uname 匹配，输出 `aarch64-unknown-linux-ohos`

### 0004-config.sub.patch
**目的**: 添加 ohos-linux triplet 支持
**修改文件**: `config.sub`
**关键修改**: 添加 `ohos*` 和 `linux-ohos*-` 模式匹配

### 0005-configure.patch
**目的**: automake 版本兼容性修复（1.17→1.16 降级相关变更）
**修改文件**: `configure`

### 0006-depcomp.patch ~ 0008-missing.patch
**目的**: 修复 build-aux 脚本 shebang 兼容性
**修改文件**: `depcomp`、`install-sh`、`missing`

### 0009-termcap.h.patch
**目的**: 为 HarmonyOS 提供最小 termcap.h 声明（系统无 ncurses/termcap 头文件）
**修改文件**: 新增 `termcap.h`
**关键修改**: 声明 `tgetent`/`tgetflag`/`tgetnum`/`tgetstr`/`tgoto`/`tputs`/`tparam` 函数，链接系统 `libtinfo.so.6`

### 0010-configure-umask.patch
**目的**: 修复 HMDFS 文件系统权限问题
**修改文件**: `configure`
**关键修改**: 将临时目录创建的 `umask 077` 改为 `umask 022`，解决 config.status 无法写入临时文件的问题

## 遇到的问题

### 问题1: config.status 无法创建临时子目录

**现象**: configure 执行时 config.status 报错无法创建临时目录
**原因**: HMDFS 文件系统限制，umask 077 导致目录权限不足
**解决**: 应用 0010-configure-umask.patch 将 umask 从 077 改为 022

### 问题2: config.guess 不识别 HarmonyOS

**现象**: configure 无法识别当前系统为 HarmonyOS
**原因**: 上游 config.guess 版本未包含 OHOS 支持
**解决**: 应用 0003-config.guess.patch 添加 `__OHOS__` 宏检测和 HarmonyOS uname 匹配

## 测试结果

详见 test_package/ 目录中的 Conan L1 测试。

| 测试项 | 结果 |
|--------|------|
| conan create 编译 | ✅ |
| test_package (history_init/H_ENTER/H_ADD/history_end) | ✅ |

## 验证安装

```bash
# 检查安装
ls -la $HOME/usr/local/lib/libedit*
ls $HOME/usr/local/include/histedit.h
```

## 经验总结

1. autotools 项目的 config.guess/config.sub 补丁是 HarmonyOS 适配的标准操作
2. HMDFS 文件系统限制可能导致 configure 脚本中的目录操作失败，需检查 umask 设置
3. build-aux 脚本（compile/depcomp/install-sh/missing）的 shebang 修复是常见适配点

## 参考资料

- https://thrysoee.dk/editline/
- https://github.com/troglobit/editline
