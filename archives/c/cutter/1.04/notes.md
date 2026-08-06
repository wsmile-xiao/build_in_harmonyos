# cutter 1.04 适配笔记

## 编译环境
- 构建系统: makefile (simple single-file C program)
- 编译日期: 2026-08-06
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
source .build-context-cutter-1.04
cd $BUILD_SRC_DIR
make CC=clang CFLAGS="-fPIC -O2"
make install DESTDIR=$TEST_PREFIX PREFIX=
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile hardcodes `cc` | Original Makefile uses `cc` instead of `$(CC)` | Modified Makefile to use `$(CC)` and `$(CFLAGS)`, added install target |
| 2 | Redefinition of `struct sockaddr_storage` | `<linux/tcp.h>` includes `<linux/socket.h>` which conflicts with `<sys/socket.h>` on Bionic | Define `_UAPI_LINUX_SOCKET_H` before including linux headers to skip the kernel socket header |
| 3 | Redefinition of `struct ethhdr` | `<linux/if_ether.h>` and `<net/ethernet.h>` both define `struct ethhdr` | Removed `<linux/if_ether.h>`, keep `<net/ethernet.h>` |
| 4 | sscanf format mismatch | `%8lx` expects `unsigned long *` but `in_addr_t` is `unsigned int` | Changed `%8lx` to `%8x` |
| 5 | `time()` undeclared | Missing `#include <time.h>` | Added `#include <time.h>` |
| 6 | `addrlen` type mismatch | `int` vs `socklen_t *` for `recvfrom` | Changed `int addrlen` to `socklen_t addrlen` |

## 源码修改

- `patches/0001-Makefile.patch`: Makefile fixes (use $(CC)/$(CFLAGS), add install target)
- `patches/0002-cutter.c.patch`: cutter.c header/config fixes

## 依赖版本

无外部依赖，仅依赖 libc 和 Linux 内核头文件。

## 验证结果

```bash
$ $TEST_PREFIX/bin/cutter

cutter - TCP/IPv4 connection cutter for linux firewalls

Version   : 1.04
Home page : http://www.digitage.co.uk/cutter

usage is: cutter ip [ port [ ip [ port ] ] ]
```

## 注意事项

- cutter 是命令行工具（非库），已创建 commands.json (R38)
- cutter 需要 root 权限和 IP 转发启用才能实际运行
- 源码来自 Debian snapshot 镜像（官方网站 digitage.co.uk 已下线）
