# basez

## 概述
basez 是一个 base16/base32/base64 编码/解码命令行工具，完整实现了 RFC 4648 中定义的所有编码格式，包括:
- Base16 (hexadecimal)
- Base32 (plain and hex variants)
- Base64 (plain, URL-safe, MIME, PEM variants)

## 版本
- 1.6.2 (2019-10-05)

## 来源
- https://codeberg.org/vonshedknocker/basez
- 许可证: GPL-3.0-or-later

## 构建依赖
- 无外部依赖（纯 C，仅 libc）
- clang (鸿蒙平台)

## 构建说明
basez 使用自定义 configure 脚本（非 autotools）配合 Makefile.src 模板构建。
configure 脚本接受 CC=, CFLAGS=, CPPFLAGS=, LDFLAGS= 作为命令行参数，
并从 Makefile.src 生成 Makefile。无需源码补丁。

## 功能
- Base16 编码/解码 (hex)
- Base32 编码/解码 (plain + hex alphabet)
- Base64 编码/解码 (plain + URL-safe + MIME + PEM)
- 从 stdin 读取，输出到 stdout
- 支持编码和解码双向操作
