# libslirp

## 简介

libslirp 是一个通用的 TCP-IP 模拟器，主要用于 QEMU 虚拟机中提供网络功能。它实现了 TCP/IP 协议栈的用户态模拟。

## 功能概述

- TCP/IP 协议栈模拟
- SLIRP（Simple Low-Level Internet Protocol）实现
- 支持 IPv4 和 IPv6
- DHCP 和 BOOTP 支持
- TFTP 支持
- NCSI（Network Controller Sideband Interface）支持

## OHOS 适配

- 构建系统：meson
- 编译器：clang/clang++
- 依赖：glib-2.0 >= 2.0
- 无特殊补丁需求
- 库文件：libslirp.so

## 依赖关系

### 编译依赖
- glib-2.0 >= 2.0
- meson >= 0.50
- ninja

### 运行依赖
- glib-2.0

## 参考资料

- 官网：https://gitlab.freedesktop.org/slirp/libslirp
- GitHub：https://github.com/qemu/libslirp
- 文档：https://qemu.readthedocs.io