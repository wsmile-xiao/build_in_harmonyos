# libnfnetlink

## 简介

libnfnetlink 是一个低级别的用户空间库，为需要与 Linux netfilter 子系统通信的应用程序提供简单 API。
它是 iptables、conntrack 等 netfilter 工具的基础依赖库。

## 描述

Low-level library for netfilter related communication - 一个用户空间库，
为需要与 netfilter 子系统通信的应用程序提供简单 API。

主要功能：
- 提供 netlink socket 与内核 netfilter 模块通信的接口
- 尕装 netlink 消息的构建、发送、接收和解析
- 提供接口名称与索引映射查询功能（nlif_* 系列）

## 主页

https://www.netfilter.org/projects/libnfnetlink/

## 许可证

LGPL-2.1-or-later

## 构建系统

autotools (configure + make)

## 依赖

无特殊依赖，仅需要：
- C 编译器 (clang/gcc)
- 标准 C 库
- 内核头文件（linux/netlink.h）

## API 概览

### 核心 netlink 函数 (nfnl_*)

```c
struct nfnl_handle *nfnl_open(void);         // 打开 netlink 连接
void nfnl_close(struct nfnl_handle *h);      // 关闭连接
int nfnl_send(struct nfnl_handle *h, ...);   // 发送消息
int nfnl_recv(struct nfnl_handle *h, ...);   // 接收消息
int nfnl_fd(struct nfnl_handle *h);          // 获取文件描述符
```

### 接口查询函数 (nlif_*)

```c
struct nlif_handle *nlif_open(void);         // 打开接口查询
void nlif_close(struct nlif_handle *h);      // 关闭
int nlif_index2name(struct nlif_handle *h, int idx, char *name); // 索引转名称
```

### 属性处理函数

```c
int nfnl_addattr_l(struct nlmsghdr *n, ...); // 添加属性
int nfnl_addattr8/16/32(...);                // 添加特定大小属性
int nfnl_parse_attr(...);                    // 解析属性
```

## 使用示例

```c
#include <libnfnetlink/libnfnetlink.h>

// 打开 netlink 连接
struct nfnl_handle *h = nfnl_open();
if (!h) {
    perror("nfnl_open");
    exit(1);
}

// 发送消息到 netfilter 子系统
// ... 构建消息 ...
nfnl_send(h, nh, nh->nlmsg_len);

// 接收响应
nfnl_recv(h, buf, sizeof(buf));

// 关闭连接
nfnl_close(h);
```

## 编译链接

```bash
# 使用 pkg-config
gcc myapp.c $(pkg-config --cflags --libs libnfnetlink) -o myapp

# 或手动指定
gcc myapp.c -I/usr/local/include/libnfnetlink \
    -L/usr/local/lib -lnfnetlink -o myapp
```

## 版本历史

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|----------|------|
| 1.0.2 | built | 2026-06-09 | 当前稳定版，已通过 HarmonyOS 适配 |

## HarmonyOS 适配说明

### 需要的补丁

1. **config.guess 补丁**: 添加 HarmonyOS 系统识别
2. **头文件冲突补丁**: 解决 `linux/socket.h` 和 `sys/socket.h` 的 `sockaddr_storage` 重复定义

### 关键修改

在源码中添加宏保护：
```c
#ifndef __kernel_sa_family_t
typedef unsigned short __kernel_sa_family_t;
#endif
#ifndef _UAPI_LINUX_SOCKET_H
#define _UAPI_LINUX_SOCKET_H
#endif
```

### 注意事项

- 需要内核头文件支持（linux/netlink.h）
- 测试程序需要 netlink socket 权限（root 或 CAP_NET_ADMIN）
- 纯库文件，无可执行程序

## 文件列表

安装后的文件结构：
```
usr/local/
├── lib/
│   ├── libnfnetlink.so -> libnfnetlink.so.0.2.0
│   ├── libnfnetlink.so.0 -> libnfnetlink.so.0.2.0
│   ├── libnfnetlink.so.0.2.0 (36KB)
│   ├── libnfnetlink.la
│   └── pkgconfig/libnfnetlink.pc
└── include/
    └── libnfnetlink/
        ├── libnfnetlink.h
        ├── linux_nfnetlink.h
        └── linux_nfnetlink_compat.h
```

## 相关项目

- libnetfilter_conntrack - 连接跟踪库（依赖 libnfnetlink）
- libnetfilter_queue - 数据包队列库（依赖 libnfnetlink）
- iptables - 防火墙工具（使用 libnfnetlink）
- nftables - 新一代防火墙工具

## 参考文档

- netfilter 官方文档: https://www.netfilter.org/documentation/
- libnfnetlink API 文档: https://www.netfilter.org/projects/libnfnetlink/doxygen/

---
最后更新: 2026-06-09