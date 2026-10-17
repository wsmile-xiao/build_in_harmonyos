# traceroute 2.1.6 - HarmonyOS 适配

## 概述

traceroute 是网络路由追踪工具，用于探测数据包从源到目的端的路径。支持 UDP、ICMP、TCP、DCCP 等多种探测模式。

**编译状态**: ✅ 编译通过

## 编译环境

| 项目 | 值 |
|------|-----|
| 系统 | HarmonyOS HongMeng Kernel aarch64 |
| 编译器 | clang 15.0.4 |
| C 库 | musl libc |
| 构建系统 | makefile |

## 编译步骤

```bash
# 下载源码
wget https://deb.debian.org/debian/pool/main/t/traceroute/traceroute_2.1.6.orig.tar.gz

# 应用补丁
patch -p1 < patches/0001-Make.rules.patch

# 编译
make env=yes CC=clang -j1

# 安装
make install prefix=$PREFIX
```

## 验证

```bash
$ traceroute --version
Modern traceroute for Linux, version 2.1.6
Copyright (c) 2016  Dmitry Butskoy,   License: GPL v2 or any later
```

## 注意事项

1. **权限需求**: traceroute 需要 raw socket 权限发送 UDP/ICMP 包。
2. **UDP 模式**: 默认使用 UDP 协议。
3. **功能完整**: 支持 UDP、ICMP、TCP、DCCP 等多种探测模式。
