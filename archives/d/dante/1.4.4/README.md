# dante 1.4.4 — OpenHarmony 预编译包

SOCKS server and client, implementing RFC 1928 and related standards.

## 基本信息

- **版本**: 1.4.4
- **许可证**: BSD-Inferno-Nettverk
- **构建系统**: autotools
- **平台**: aarch64-unknown-linux-ohos (OpenHarmony)
- **编译日期**: 2026-06-08
- **编译状态**: built

## 产物内容

### 可执行文件
- `sbin/sockd` — SOCKS5 代理服务端守护进程

### 共享库
- `lib/libdsocks.so` — SOCKS客户端预加载库（LD_PRELOAD透明代理）
- `lib/libsocks.so.0.1.1` — SOCKS协议共享库（Rconnect/Rbind等API）

### 静态库
- `lib/libsocks.a` — SOCKS协议静态库

### 头文件
- `include/socks.h` — SOCKS C API头文件

### 文档
- `share/man/man8/sockd.8` — sockd服务端手册
- `share/man/man1/socksify.1` — socksify客户端手册
- `share/man/man5/sockd.conf.5` — sockd配置手册
- `share/man/man5/socks.conf.5` — socks配置手册

## 安装方法

```bash
# 解压预编译包到目标路径
tar xzf dante-1.4.4-ohos-aarch64.tar.gz -C /usr/local

# 验证安装
/usr/local/sbin/sockd -v
# 预期输出: Dante v1.4.4.  Copyright (c) 1997 - 2024, Inferno Nettverk A/S, Norway.
```

## 使用示例

### sockd 服务端
```bash
# 配置验证
sockd -V -f /etc/sockd.conf

# 以daemon模式运行
sockd -D -f /etc/sockd.conf
```

### socksify 客户端（LD_PRELOAD透明代理）
```bash
LD_PRELOAD=/usr/local/lib/libdsocks.so curl http://example.com
```

### C API
```c
#include <socks.h>
SOCKSinit("myapp");
Rconnect(sockfd, addr, addrlen);
```

## 功能限制（OHOS平台）

1. **TCP resolver协议不可用**: 因 HAVE_NO_RESOLVESTUFF=1，sockd.conf 中 `resolve.protocol tcp` 不支持
2. **CPU affinity不可用**: 因 HAVE_SCHED_SETAFFINITY=0，affinity相关配置不支持
3. **sockd需root权限启动**: 安全设计要求，配置验证(-V)可在非root下运行

## 依赖

仅依赖 libc.so (musl libc)，无其他外部库依赖。

## 编译细节

详见 `notes.md` 和 `reports/test-report.md`。