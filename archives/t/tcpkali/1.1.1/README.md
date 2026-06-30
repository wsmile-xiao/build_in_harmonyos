# tcpkali 1.1.1 — OpenHarmony (OHOS) aarch64 预编译包

## 简介

tcpkali 是一个高性能 TCP/WebSocket 负载测试工具，基于 libev 事件循环库，支持多连接并发、消息速率控制、延迟测量、带宽限制、WebSocket (RFC6455) 协议等功能。

本次预编译版本针对 OpenHarmony (OHOS) aarch64 平台进行适配，使用 OHOS 交叉编译工具链 clang 15.0.4 编译。

## 编译信息

- **构建系统**: autotools
- **编译器**: clang 15.0.4 (OHOS 交叉编译工具链)
- **目标平台**: aarch64-unknown-linux-ohos
- **libc**: musl libc (OHOS 系统自带)
- **依赖**: ncurses 6.4 (静态链接)

## 适配修改

为适配 OHOS 平台，对源码做了以下修改：

1. **deps/libcows/buffers.c**: 添加 `#include <stddef.h>` 及 OHOS 兼容的 `__containerof`/`QUEUE_TYPEOF` 宏定义，解决 OHOS musl libc `sys/queue.h` 缺失这两个宏的问题。

2. **src/tcpkali_syslimits.c**: 用 `#ifdef HAVE_SYS_SYSCTL_H` 守卫 `#include <sys/sysctl.h>`，解决 OHOS musl libc 不提供该头文件的问题。

详细补丁内容见 `patches/` 目录。

## 预编译包内容

| 文件 | 大小 | 说明 |
|------|------|------|
| `tcpkali-1.1.1-ohos-aarch64.tar.gz` | 331KB | 主产物包（包含 ELF 二进制） |
| `tcpkali-1.1.1-ohos-aarch64-debug.tar.gz` | 72KB | debug 符号包 |

## 安装方式

解压主产物包到目标路径即可使用：

```bash
tar xzf tcpkali-1.1.1-ohos-aarch64.tar.gz -C /usr/local
```

## 基本使用

```bash
# 查看版本
tcpkali --version

# 启动 TCP 负载测试
tcpkali -c 100 -T 10s 192.168.1.1:8080

# 启动 WebSocket 负载测试
tcpkali -c 50 --ws -T 10s 192.168.1.1:8080/ws

# 监听模式
tcpkali -l 8080
```

## 测试结果

完整测试报告见 `reports/test-report.md`。所有核心功能测试通过：
- TCP 连接管理与并发测试
- WebSocket (RFC6455) 协议支持
- 消息发送与速率控制
- 带宽与延迟测量
- OHOS 平台标识与动态链接验证
