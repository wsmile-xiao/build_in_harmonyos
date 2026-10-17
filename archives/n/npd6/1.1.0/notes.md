# npd6 1.1.0 适配笔记

## 编译环境
- 构建系统: makefile (plain Makefile)
- 编译日期: 2026-08-07
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
# Source the build context
source .build-context-npd6-1.1.0

# Build with clang and required flags
cd $BUILD_SRC_DIR
make CC=clang CFLAGS="-Wall -g -O3 -fPIC -fcommon"

# Install to test prefix
make install DESTDIR=$TEST_PREFIX INSTALL_PREFIX=/usr

# Verify binary
$TEST_PREFIX/usr/bin/npd6 --version
# Output: npd6 - version 1.1.0
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `sys/sysctl.h` not found | OHOS doesn't have this deprecated header | Guard with `#if __has_include(<sys/sysctl.h>)` — not used in code |
| 2 | `sockaddr_storage` redefinition | `linux/netlink.h` includes `linux/socket.h` which conflicts with `sys/socket.h` | Remove unused `#include <linux/netlink.h>` from includes.h |
| 3 | Duplicate symbols at link time | npd6.h defines global variables without `extern` (common symbol behavior) | Add `-fcommon` to CFLAGS for clang/lld compatibility |
| 4 | `svnversion: No such file or directory` | Makefile uses `svnversion` for build version string | Remove `$(shell svnversion -n .)` from DEV definition |

## 源码修改

| 补丁文件 | 修改内容 |
|---------|---------|
| 0001-Makefile.patch | Remove svnversion dependency from build version flag |
| 0002-includes.h.patch | Guard sys/sysctl.h include; remove unused linux/netlink.h include |

## 依赖版本

无外部依赖 — npd6 只使用标准 C 库和 Linux 内核头文件。

## 验证结果

```bash
$ npd6 --version
npd6 - version 1.1.0
Copyright (C) 2011-2013 Sean Groarke
```

## 注意事项

- npd6 是一个网络守护进程，需要 root 权限和 raw socket 能力才能运行
- -fcommon 标志是必需的，因为 npd6.h 在头文件中定义了全局变量（而非 extern 声明）
- linux/netlink.h 被移除是因为它不被代码使用，且会导致 socket.h 重定义冲突

---

**编译结束**: 2026-08-07 06:03
**最终状态**: built
