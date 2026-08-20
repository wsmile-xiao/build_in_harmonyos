# krb5 for HarmonyOS

## 概述

MIT Kerberos 5 在 HarmonyOS/OpenHarmony (aarch64) 上的编译记录。

**可用版本**:
- **1.22.1**: Conan 配方适配，支持动态/静态链接
- **1.22.2**: 已编译但未进行 Conan 适配

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | MIT Kerberos 5 |
| 官网 | https://web.mit.edu/kerberos/ |
| 下载 | https://web.mit.edu/kerberos/dist/krb5/1.22/krb5-1.22.1.tar.gz |
| 许可证 | MIT |

## 关键修复

### 1. config.guess/config.sub 不支持 HarmonyOS
更新到 2025 版本，添加 HarmonyOS 识别和 ohos-linux triplet。

### 2. TMPDIR umask 077 问题 (E082)
HarmonyOS 上 umask 077 + SGID 导致 mktemp 创建的临时目录权限不可写。
修复 configure 脚本：设置可写 TMPDIR、umask 改为 022、使用绝对路径。

### 3. dnsglue.c musl libc 兼容性
musl libc 不支持 _res 全局变量，修改 PRIMARY_DOMAIN 宏返回 NULL。

## 编译步骤

```bash
# 1. 解压源码（源码在 src/ 子目录）
tar xzf krb5-1.22.1.tar.gz
cd krb5-1.22.1/src

# 2. 应用补丁
patch -p1 < patches/0001-config-config.guess.patch
patch -p1 < patches/0002-config-config.sub.patch
patch -p1 < patches/0003-configure.patch
patch -p1 < patches/0004-lib-krb5-os-dnsglue.c.patch

# 3. 设置环境
export TMPDIR=$HOME/tmp
export CC=clang
export CFLAGS="-fPIC -O2"

# 4. 配置和编译
./configure --prefix=$HOME/usr/local
make -e -j1
make install
```

## 产物

| 类型 | 文件 |
|------|------|
| 库 | libkrb5.so, libgssapi_krb5.so, libk5crypto.so, libcom_err.so 等 |
| 工具 | kinit, klist, kadmin, kdestroy, kpasswd, kvno 等 |
| 头文件 | krb5.h, gssapi.h, com_err.h 等 |
