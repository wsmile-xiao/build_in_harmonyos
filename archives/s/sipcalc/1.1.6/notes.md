# sipcalc 1.1.6 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-03
- 编译器: clang/clang++ (clang 15.0.4)
- 状态: published
- 源码URL: https://deb.debian.org/debian/pool/main/s/sipcalc/sipcalc_1.1.6.orig.tar.gz
- License: BSD-3-Clause

## 编译步骤

```bash
# 加载构建上下文
source .build-context-sipcalc-1.1.6
export LD_LIBRARY_PATH=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib:/storage/Users/currentUser/usr/local/lib:/data/service/hnp/magic-cli.org/magic-cli_1.0.0/lib:
export TMPDIR=$HOME/tmp

cd $BUILD_SRC_DIR
./configure --prefix=$DEFAULT_PREFIX
make -j1
make install DESTDIR=$TEST_PREFIX
make check  # No test suite
make install  # Local deployment (no DESTDIR)
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure: C compiler cannot create executables | OHOS SDK lld linker depends on libxml2.so.16 but LD_LIBRARY_PATH didn't include SDK's llvm/lib | Add `/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib` to LD_LIBRARY_PATH |
| 2 | config.status: can't create ./confXXXXXX/subs1.awk: Permission denied | HMDFS: mktemp with umask 077 creates dir owned by UID 20001006 with 070 perms, but process UID is 20020082. chmod also fails on HMDFS (E046) | Patch configure to use `${TMPDIR:-$HOME/tmp}/confXXXXXX` for tmp dir and remove `umask 077` so dir gets group-writable perms (drwxrws--x) accessible by file_manager group |
| 3 | 原始下载URL不可达 | routemeister.net URL timed out | Use Debian mirror: https://deb.debian.org/debian/pool/main/s/sipcalc/sipcalc_1.1.6.orig.tar.gz |

## 源码修改

### configure (1 file modified)

- **修改内容**: 将 `mktemp -d "./confXXXXXX"` 改为 `mktemp -d "${TMPDIR:-$HOME/tmp}/confXXXXXX"`，并移除 `umask 077`
- **修改原因**: HMDFS 文件系统中，umask 077 创建的目录所有权为 UID 20001006（HMDFS元数据UID），而进程运行 UID 为 20020082，导致无写权限。使用 TMPDIR 路径避免 HMDFS 权限问题，不使用 umask 077 使目录获得组可写权限。
- **补丁状态**: tracked by ohc-run.py track-edit

## 依赖版本

sipcalc 无外部依赖，仅需要标准 C 库和 POSIX 网络头文件。

构建工具依赖:
- clang 15.0.4 (OHOS SDK)
- GNU Make 4.4.1
- autoconf 2.72 / automake 1.17

## 验证结果

### make check

```bash
$ make check 2>&1
Making check in doc
make[1]: Nothing to be done for 'check'.
Making check in include
make[1]: Nothing to be done for 'check'.
Making check in src
make[1]: Nothing to be done for 'check'.
```

sipcalc 无自带测试套件，"Nothing to be done for 'check'" 为正常输出。

### 安全弹窗验证 (R7)

```bash
$ $STAGING_PREFIX/bin/sipcalc --version
sipcalc 1.1.6
Written by Simon Ekstrand.
Copyright (C) 2003-2013 Simon Ekstrand.
```

安全弹窗已触发并确认通过。

### 版本验证

```bash
$ $DEFAULT_PREFIX/bin/sipcalc --version
sipcalc 1.1.6
Written by Simon Ekstrand.
Copyright (C) 2003-2013 Simon Ekstrand.
This is free software; see the source for copying conditions.
```

### IPv4 子网计算

```bash
$ $DEFAULT_PREFIX/bin/sipcalc 192.168.1.1/24
-[ipv4 : 192.168.1.1/24] - 0

[CIDR]
Host address		- 192.168.1.1
Host address (decimal)	- 3232235777
Host address (hex)	- C0A80101
Network address		- 192.168.1.0
Network mask		- 255.255.255.0
Network mask (bits)	- 24
Network mask (hex)	- FFFFFF00
Broadcast address	- 192.168.1.255
Cisco wildcard		- 0.0.0.255
Addresses in network	- 256
Network range		- 192.168.1.0 - 192.168.1.255
Usable range		- 192.168.1.1 - 192.168.1.254
```

### IPv6 地址计算

```bash
$ $DEFAULT_PREFIX/bin/sipcalc 2001:db8::1/64
-[ipv6 : 2001:db8::1/64] - 0

[IPV6 INFO]
Expanded Address	- 2001:0db8:0000:0000:0000:0000:0000:0001
Compressed address	- 2001:db8::1
Subnet prefix (masked)	- 2001:0db8:0:0:0:0:0:0/64
Prefix length		- 64
Address type		- Aggregatable Global Unicast Addresses
Network range		- 2001:0db8:0000:0000:0000:0000:0000:0000 -
			  2001:0db8:0000:0000:ffff:ffff:ffff:ffff
```

### ELF 二进制信息

```bash
$ file $DEFAULT_PREFIX/bin/sipcalc
/storage/Users/currentUser/usr/local/bin/sipcalc: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| packaging/sipcalc-1.1.6-ohos-aarch64.tar.gz | 97,825 bytes (~95KB) | 预编译包（含 ELF 签名） |
| packaging/sipcalc-1.1.6-ohos-aarch64-debug.tar.gz | 31,255 bytes | 调试符号包 |
| patches/0001-configure.patch | 923 bytes | HMDFS TMPDIR 适配补丁 |

## 注意事项

1. **HMDFS 权限问题（平台真理 L1）**: HMDFS 上 `umask 077 && mktemp -d` 创建的目录权限为 070，owner UID 为 20001006（HMDFS元数据UID），chmod 777 无效（E046）。autotools 项目的 configure/config.status 需要将 tmp 目录创建在 `$TMPDIR`（不在 HMDFS 挂载点）并去掉 umask 077。
2. **LD_LIBRARY_PATH 必须包含 OHOS SDK llvm/lib**: lld 链接器依赖 libxml2.so.16，需要将 SDK 的 lib 路径加入 LD_LIBRARY_PATH。
3. **原始下载URL不可达**: routemeister.net 服务器超时，需使用 Debian 镜像源。
---

**编译结束**: 2026-06-03 18:36
**最终状态**: published
