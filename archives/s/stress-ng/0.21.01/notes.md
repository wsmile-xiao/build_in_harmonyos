# stress-ng 0.21.01 编译笔记

## 编译环境
- 版本：0.21.01
- 构建系统：Makefile
- 编译器：clang 15.0.4
- 目标平台：aarch64-linux-ohos

## 平台适配问题

### E091: sockaddr_storage/sysinfo 重定义冲突

**问题**：OpenHarmony 内核头文件 `linux/socket.h` 和 `linux/sysinfo.h` 定义了与 musl libc 冲突的结构体。

**影响文件**：
- stress-af-alg.c (linux/socket.h)
- stress-close.c (linux/netlink.h)
- stress-fd-abuse.c (linux/netlink.h)
- stress-netlink-proc.c (linux/netlink.h)
- stress-sockdiag.c (linux/netlink.h)
- stress-netlink-task.c (linux/genetlink.h)
- stress-get.c (linux/sysctl.h)
- stress-syscall.c (linux/sysctl.h)

**修复方案**：
在包含冲突头文件前，使用宏重命名结构体：
```c
#ifdef __OHOS__
#define sysinfo __linux_sysinfo
#define sockaddr_storage __linux_sockaddr_storage
#endif
#include <linux/netlink.h>
#ifdef __OHOS__
#undef sysinfo
#undef sockaddr_storage
#endif
```

### __packed 重复符号错误

**问题**：OpenHarmony 内核头文件 `linux/android/binder.h` 和 `linux/userfaultfd.h` 将 `__packed` 定义为变量而非宏。

**影响文件**：
- stress-binderfs.c
- stress-userfaultfd.c
- stress-syscall.c

**修复方案**：
在包含冲突头文件前，将 `__packed` 重定义为宏：
```c
#ifdef __OHOS__
#define __packed __attribute__((packed))
#endif
#include <linux/userfaultfd.h>
#ifdef __OHOS__
#undef __packed
#endif
```

### PREFIX 路径适配

**问题**：Makefile 硬编码安装路径 `/usr/bin`。

**修复方案**：
修改 Makefile 使用 PREFIX 变量：
```makefile
PREFIX ?= /usr
BINDIR=$(PREFIX)/bin
```

## 编译结果

- 编译状态：成功
- 二进制大小：3.0M
- 质量门禁：G1-G3 PASS，G4 FAIL（需补充归档文件）

## 知识提取

发现新错误模式：OpenHarmony 内核头文件 `__packed` 变量定义导致链接重复符号错误。

## 后续工作

1. 完成预编译包制作
2. 本地安装验证
3. finish 收尾流程
---

**编译结束**: 2026-07-15 17:11
**最终状态**: built
