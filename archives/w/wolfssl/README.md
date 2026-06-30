# wolfSSL — Embedded SSL/TLS Library

**类别**: 安全/加密库
**许可证**: GPL-3.0-or-later
**语言**: C/C++
**构建系统**: autotools

## 简介

wolfSSL 是一个轻量级、高性能、可移植的 SSL/TLS 库，用 ANSI C 编写，面向嵌入式和 IoT 环境。支持 TLS 1.3 和 DTLS 1.3，体积仅为 OpenSSL 的 1/20 左右。

## 已编译版本

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 5.9.0 | published | 2026-06-06 | 首次鸿蒙编译，纯库软件 |

## 主要特性

- TLS 1.0 / 1.1 / 1.2 / 1.3 全协议支持
- DTLS 1.0 / 1.2 / 1.3 支持
- OpenSSL 兼容 API 层（wolfssl/openssl/ 头文件）
- FIPS 140-3 认证选项
- 后量子密码学（Dilithium / Falcon / SPHINCS+ / ML-KEM）
- ARM NEON/ARM Crypto 扩展优化
- QUIC 协议支持
- 最小依赖：仅 libc.so（无额外运行时库依赖）

## 鸿蒙适配要点

- wolfssl 是纯库软件（bin/ 中无 ELF 可执行文件，只有 wolfssl-config shell 脚本）
- autotools 构建，GitHub archive 需先 autoreconf
- E011: configure/config.status 需 umask 077 → umask 022（HMDFS 权限问题）
- E010: 必须使用 CONFIG_SHELL=bash（toybox sh 不兼容 libtool）
- E004: LD_LIBRARY_PATH 需包含 OHOS SDK llvm/lib（lld 依赖 libxml2.so.16）