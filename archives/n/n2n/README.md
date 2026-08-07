# n2n 3.1.1 for HarmonyOS

## 概述

n2n 是一款轻量级 P2P VPN 软件，使用 UDP 在边缘节点间建立直接的点对点连接。
由 ntop 开发，支持 AES/ChaCha20 加密。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | n2n |
| 版本 | 3.1.1 |
| 下载地址 | https://github.com/ntop/n2n/archive/refs/tags/3.1.1.tar.gz |
| 官方文档 | https://github.com/ntop/n2n |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS 6.0 (aarch64) |
| 编译器 | clang 15 |
| 构建系统 | CMake |

## 功能说明

| 组件 | 状态 | 说明 |
|------|------|------|
| supernode | ✅ 完全可用 | VPN 协调节点，不依赖 TUN/TAP |
| edge | ⚠️ 功能受限 | VPN 客户端，TUN/TAP 不可用导致隧道功能无法使用，但可编译运行 |
| 加密 (AES/ChaCha20) | ✅ 可用 | 通过 OpenSSL 1.1.1w |
| 路由管理 | ❌ 不可用 | OHOS 不提供 netlink API |

## 依赖

- openssl/1.1.1w
