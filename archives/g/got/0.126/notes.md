# got 0.126 编译笔记

## 编译环境

- 平台: OHOS/Linux aarch64
- 内核: HongMeng Kernel 1.12.0
- 编译器: clang
- 构建系统: autotools

## 编译过程

### 1. 源码准备

源码来自 got-portable 0.126 tarball，解压到 `/storage/Users/currentUser/builds/got-0.126.work`

### 2. 依赖安装

使用预编译包安装依赖：
- libbsd 0.11.7
- libmd 1.1.0
- libretls 3.8.1
- libevent 2.1.12 (手动编译)
- libuuid 1.47.0 (手动编译)

### 3. 编译问题与修复

#### 问题 1: SHA2_CTX 未定义

**文件**: `compat/sha2.c`
**原因**: aarch64 架构上 sha2.h 头文件路径问题
**修复**: 在文件开头添加 `#include "sha2.h"`

#### 问题 2: SHA256_Init/Update/Final 与 OpenSSL 冲突

**文件**: `include/got_compat2.h`
**原因**: OpenSSL 已定义 SHA256_Init 等函数，重复定义导致冲突
**修复**: 
- 添加 `__OHOS__` 和 `__linux__` 到 openssl/sha.h 包含条件
- 添加 `#ifndef HAVE_SHA256UPDATE` 条件包含 compat/sha2.h

#### 问题 3: 链接时 SHA256_Init 等未定义

**文件**: 各目录 Makefile
**原因**: 未链接 libcrypto
**修复**: LDADD 添加 `$(libcrypto_LIBS)`

#### 问题 4: 运行时库加载失败

**原因**: libbsd.so.0 和 libmd.so.0 符号链接缺失
**修复**: 创建符号链接
```bash
cd /storage/Users/currentUser/usr/local/lib
ln -s libbsd.so.0.11.7 libbsd.so.0
ln -s libmd.so.0.1.0 libmd.so.0
```

#### 问题 5: HMDFS 权限问题

**文件**: `template/configure`
**原因**: umask 077 导致无法创建临时文件
**修复**: `sed -i 's/umask 077/umask 022/g' configure`

#### 问题 6: template 子目录配置

**文件**: `template/got_compat.h`
**原因**: size_t 未定义
**修复**: 添加 `#include <stddef.h>`

#### 问题 7: gotwebd 编译失败

**原因**: template 子目录需要独立 configure
**修复**: 
- 清理 template 目录配置缓存
- 使用独立构建目录配置 template
- 复制构建文件回源目录

### 4. 编译结果

所有核心组件编译成功：
- got, gotadmin, gotctl, gotsh, gitwrapper, tog
- gotd, gotwebd
- 16 个 libexec 程序

验证：
```
LD_LIBRARY_PATH=/storage/Users/currentUser/usr/local/lib got --version
输出: got 0.126
```

### 5. 安装

安装到 `/storage/Users/currentUser/usr/local`：
- bin/: got, gotadmin, gotctl, gotsh, gitwrapper, tog
- sbin/: gotd, gotwebd, gotwebctl
- libexec/: 16 个 got-* 程序
- share/man/: 手册页

## 知识提取

本次编译发现的通用问题：

1. **SHA2 平台适配**: aarch64 架构需要特殊处理 sha2.h 头文件路径
2. **OpenSSL 冲突**: 使用 OpenSSL SHA 函数时需避免重复定义
3. **HMDFS umask**: autotools configure 需要修改 umask 077 → umask 022
4. **AC_CONFIG_SUBDIRS**: 子目录独立配置需要特殊处理

---
