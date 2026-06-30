# iodine — 通过 DNS 服务器隧道传输 IPv4 数据

## 基本信息

| 字段 | 值 |
|------|------|
| 软件 | iodine |
| 版本 | 0.8.0 |
| License | ISC |
| Homepage | https://code.kryo.se/iodine |
| 构建系统 | makefile（简单 Makefile） |
| 编译器 | clang |
| 依赖 | zlib/1.3.1 |
| 平台 | OpenHarmony aarch64 |

## 简介

iodine 是一个将 IPv4 数据通过 DNS 协议隧道传输的工具，用于在仅允许 DNS 流量的网络环境中建立 IP 隧道连接。它包含两个程序：

- **iodine**：客户端程序，通过 DNS 请求建立隧道连接
- **iodined**：服务器端程序，通过 DNS 回复传输数据

### 主要特性
- 支持多种 DNS 编码方式（Base32、Base64、Base64u、Base128、Raw）
- 支持 NULL/PRIVATE/TXT/SRV/MX/CNAME/A 等多种 DNS 记录类型
- 自动检测最佳编码和记录类型
- 支持密码认证
- 支持 IPv4 和 IPv6

## 编译信息

### 已编译版本
- **版本**: 0.8.0
- **状态**: published
- **编译日期**: 2026-06-12
- **平台**: OpenHarmony aarch64 (musl libc)

### 补丁
- `0001-src-common.c.patch`：平台适配补丁，添加 `!defined(__OHOS__)` 守卫以跳过 static daemon() 定义（因 musl libc 已提供该函数），同时修复 `do_detach()` 函数原型。

### 预编译包
- `iodine-0.8.0-ohos-aarch64.tar.gz`
- `iodine-0.8.0-ohos-aarch64-debug.tar.gz`

## 安装路径

iodine 的二进制安装到 `sbin/` 目录（网络管理工具的标准路径）：
- `$PREFIX/sbin/iodine`（客户端）
- `$PREFIX/sbin/iodined`（服务器端）
- `$PREFIX/share/man/man8/iodine.8`（man 页）
- `$PREFIX/share/doc/iodine/README.md`（文档）

## 源码

源码下载 URL: https://github.com/yarrick/iodine/archive/refs/tags/v0.8.0.tar.gz