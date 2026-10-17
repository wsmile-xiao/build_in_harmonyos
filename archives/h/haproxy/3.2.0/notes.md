# haproxy 3.2.0 适配笔记

## 编译环境
- 构建系统: makefile (custom Makefile, not autotools)
- 编译日期: 2026-08-22
- 编译器: clang/clang++
- 状态: built

## 编译步骤

使用 haproxy 的 Makefile 构建系统，TARGET=linux-musl 适配 OpenHarmony:

```bash
make TARGET=linux-musl CC=clang \
  USE_OPENSSL=1 SSL_INC=<openssl_inc> SSL_LIB=<openssl_lib> \
  USE_ZLIB=1 ZLIB_INC=<zlib_inc> ZLIB_LIB=<zlib_lib> \
  USE_PCRE2=1 USE_PCRE2_JIT=1 PCRE2_INC=<pcre2_inc> PCRE2_LIB=<pcre2_lib> \
  USE_PROMEX=1 \
  'CFLAGS=-fPIC -O2' \
  -j1
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | sockaddr_storage 重定义 | OHOS sysroot 中 <linux/socket.h> 和 <sys/socket.h> 都定义了 sockaddr_storage，netfilter 头文件引入了冲突 | 在 include/haproxy/compat.h 中，include netfilter 头文件前定义 _UAPI_LINUX_SOCKET_H 守卫 |
| 2 | pthread_setaffinity_np 未定义 | OHOS 不提供 pthread_setaffinity_np 函数，但有 sched_setaffinity | 在 src/thread.c 中用 #ifdef __OHOS__ 守卫，使用 sched_setaffinity 替代 |

## 源码修改

- include/haproxy/compat.h: 添加 _UAPI_LINUX_SOCKET_H 守卫防止 sockaddr_storage 重定义
- src/thread.c: 使用 sched_setaffinity 替代 pthread_setaffinity_np

## 依赖版本

- openssl/1.1.1w
- zlib/1.3.1
- pcre2/10.47

## 验证结果

```bash
haproxy -v
# HAProxy version 3.2.0-e134140 2025/05/28 - https://haproxy.org/
# Running on: HarmonyOS HongMeng Kernel 1.12.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| haproxy | ~19MB | HAProxy 主程序 (ELF 64-bit arm64) |

## 注意事项

- haproxy 使用 Makefile 构建系统，非 autotools/cmake
- TARGET=linux-musl 适配 OpenHarmony (musl libc)
- 所有依赖 (openssl, zlib, pcre2) 通过 Conan 管理为静态库

最终状态: built
编译结束: 2026-08-22
