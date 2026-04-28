# dnsmasq 2.92 编译进度

**日期**: 2026-04-28
**状态**: ✅ 编译成功

## 步骤记录

| 步骤 | 状态 | 备注 |
|------|------|------|
| Step 1 init | ✅ | 源码下载、解压完成 |
| Step 2 编译 | ✅ | 需修复头文件冲突 |
| Step 3 staging | ✅ | DESTDIR 安装成功 |
| Step 4 verify | ✅ | G1-G4 质量门禁通过 |
| Step 5 package | ✅ | 521KB tar.gz 生成 |
| Step 6 deploy | ✅ | 本地安装验证成功 |
| Step 7 finish | ✅ | 归档完成 |

## 编译过程

### 1. 初始化
- 源码URL: https://thekelleys.org.uk/dnsmasq/dnsmasq-2.92.tar.gz
- 构建系统: Makefile (无 configure)
- 编译器: clang 15.0.4

### 2. 编译问题与修复

#### 问题: sockaddr_storage 重复定义
```
/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/linux/socket.h:23:8: error: redefinition of 'sockaddr_storage'
struct sockaddr_storage {
       ^
/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/sys/socket.h:377:8: note: previous definition is here
```

**根因**: OpenHarmony 系统头文件中 `linux/socket.h` 和 `sys/socket.h` 都定义了 `struct sockaddr_storage`，导致重复定义错误。

**修复**: 在 `src/netlink.c` 和 `src/ipset.c` 中添加保护宏：
```c
typedef unsigned short __kernel_sa_family_t;
#define _UAPI_LINUX_SOCKET_H
#include <linux/netlink.h>
```

### 3. 编译命令
```bash
make PREFIX=/storage/Users/currentUser/usr/local
make install PREFIX=/storage/Users/currentUser/usr/local DESTDIR=/storage/Users/currentUser/test-install-dnsmasq-2.92
```

### 4. 编译警告
- 7 个 sign-compare 警告（来自 CMSG_NXTHDR 宏）
- 非关键警告，不影响功能

### 5. 功能验证
```bash
$ /storage/Users/currentUser/usr/local/sbin/dnsmasq --version
Dnsmasq version 2.92rc3  Copyright (c) 2000-2025 Simon Kelley
Compile time options: IPv6 GNU-getopt no-DBus no-UBus no-i18n no-IDN DHCP DHCPv6 no-Lua TFTP no-conntrack ipset no-nftset auth no-DNSSEC loop-detect inotify dumpfile
```

## 补丁清单

| 补丁文件 | 类型 | 说明 |
|----------|------|------|
| 0001-src-ipset.c.patch | 平台适配 | 修复 sockaddr_storage 冲突 |
| 0002-src-netlink.c.patch | 平台适配 | 修复 sockaddr_storage 冲突 |

## 知识沉淀

### 平台真理 (L1)
- OpenHarmony/musl 系统中 `linux/socket.h` 和 `sys/socket.h` 存在 `sockaddr_storage` 重复定义问题
- 解决方案：定义 `_UAPI_LINUX_SOCKET_H` 宏跳过 linux/socket.h，手动提供 `__kernel_sa_family_t` typedef

### 模式经验 (L2)
- 包含 `<linux/netlink.h>` 的代码在 OpenHarmony 上需要此修复
- 典型文件：`netlink.c`, `ipset.c`, `nftset.c` 等

---

**编译结束**: 2026-04-28 11:25
**最终状态**: success