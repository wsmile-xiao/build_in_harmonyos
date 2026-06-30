# libax25

## 简介

libax25 是 AX.25 业余无线电协议库，提供了实现 AX.25 协议栈的核心功能。AX.25 是业余无线电通信中广泛使用的协议标准。

## 功能概述

- AX.25 地址解析和转换
- AX.25 配置管理
- 业余无线电端口配置
- ROSE 和 NET/ROM 协议支持
- 静态库实现，无需动态依赖

## OHOS 适配

- 编译方式：手动生成 Makefile（hmdfs 文件系统限制）
- 编译产物：libax25.a（核心库）+ libax25io.a（I/O 库）
- 依赖：zlib（libz.a）
- 链接方式：使用 --whole-archive 确保符号解析

## 安装

```bash
# 编译应用时链接
clang your_app.c ~/usr/local/lib/libax25.a ~/usr/local/lib/libax25io.a ~/usr/local/lib/libz.a -o your_app
```

## 参考资料

- GitHub: https://github.com/ve7fet/linuxax25