# pam-pgsql 0.7.3.2 适配笔记

## 编译概要
- **软件**: pam-pgsql 0.7.3.2 (PostgreSQL PAM 认证模块)
- **构建系统**: autotools (需先 autoreconf)
- **编译器**: clang
- **状态**: built

## 关键问题与解决方案

### 1. 源码不含 configure 脚本
原始 tarball 不含 configure（只有 configure.ac），需要 `autoreconf -fi` 生成。

### 2. PAM stub 头文件结构体重复定义 (L1)
**问题**: pam_modules.h 和 pam_appl.h 都独立定义 pam_message/pam_response/pam_conv，导致 redefinition 错误。
**解决**: 修改 pam_modules.h 移除结构体定义，改为 `#include <security/pam_appl.h>`；添加缺失的 PAM_PRELIM_CHECK(0x4000U) 和 PAM_UPDATE_AUTHTOK(0x2000U)。
**影响**: 系统级 stub 头文件修改（~/usr/local/include/security/），影响所有 PAM 依赖软件。

### 3. HMDFS umask 077 权限问题 (E046 变体, L1)
**问题**: HMDFS 上 umask 077 && mktemp -d 创建的目录权限变为 drwx--S---，无法写入文件。
**解决**: 在 config.status 生成后将 umask 077 改为 umask 022：
```bash
sed -i 's/umask 077 && mktemp/umask 022 \& mktemp/g; s/umask 077 && mkdir/umask 022 \& mkdir/g' config.status
bash ./config.status
```

### 4. _XOPEN_SOURCE 重定义 (补丁 0001)
pam_pgsql.c 定义 `_XOPEN_SOURCE` 但 SDK 已定义 `_XOPEN_SOURCE=700`，添加 `#ifndef` 守卫。

### 5. PAM conversation 函数缺失 (预期行为)
openpam_ttyconv 和 misc_conv 不可用（PAM stub 不提供），不影响 pam_pgsql.so 模块。

### 6. libtool .la 陈旧路径
libintl.la 引用不存在路径，需确保无陈旧 dependency_libs。

## 编译命令
```bash
source .build-context-pam-pgsql-0.7.3.2
cd $BUILD_SRC_DIR
autoreconf -fi
sed -i 's/umask 077 && mktemp/umask 022 \& mktemp/g; s/umask 077 && mkdir/umask 022 \& mkdir/g' configure
CONFIG_SHELL=$HOME/usr/local/bin/bash bash ./configure --prefix=$DEFAULT_PREFIX
# If config.status still fails:
sed -i 's/umask 077 && mktemp/umask 022 \& mktemp/g; s/umask 077 && mkdir/umask 022 \& mkdir/g' config.status
bash ./config.status
make -j2
make install DESTDIR=$TEST_PREFIX
```
---

**编译结束**: 2026-06-09 21:55
**最终状态**: built
