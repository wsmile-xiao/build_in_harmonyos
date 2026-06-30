# libcbor

libcbor 是一个 C 语言实现的 CBOR (Concise Binary Object Representation) 协议库。

## 简介

CBOR 是一种通用的无模式二进制数据格式，定义于 RFC 8949 (前身 RFC 7049)。
libcbor 提供完整的 CBOR 规范实现，支持 CBOR 序列 (RFC 8742)。

## 主要特性

- 完全符合 IETF RFC 8949 (STD 94) 规范
- 支持 CBOR 序列 (RFC 8742)
- 跨平台 C99 实现
- 分层架构，既提供控制又提供便利
- 灵活的内存管理
- 无全局状态，线程友好
- 完整的 UTF-8 处理
- 支持流和增量处理
- 无运行时依赖，内存占用小

## 应用场景

- Yubico libfido2 (FIDO2 安全密钥)
- AWS C SDK
- GNOME fwupd
- QEMU
- OpenSSH
- Microsoft PowerShell
- MySQL

## 编译信息

- 构建系统: CMake
- 编译器: Clang 15.0.4
- 平台: OpenHarmony (aarch64)

## 参考链接

- 官方网站: https://github.com/PJK/libcbor
- CBOR 规范: https://cbor.io/
- 文档: https://readthedocs.org/projects/libcbor/
