# libb64 - Base64 编解码库

## 简介

libb64 是一个轻量级的 C/C++ Base64 编解码库，由 Chris Venter 开发。
它提供了高效的 Base64 编码和解码功能，采用状态机（state machine）方式实现，
可处理任意大小的数据块，适合嵌入式和资源受限环境。

## 版本
- 当前编译版本: 1.2.1

## 功能特性
- Base64 编码（`base64_encode_block`, `base64_encode_blockend`）
- Base64 解码（`base64_decode_block`）
- 状态机设计，支持分块流式处理
- 纯 C 实现，无外部依赖
- 附带命令行工具 `base64`（已重命名为 `libb64-base64` 避免与 coreutils 冲突）

## 编译信息
- 构建系统: makefile（纯 Makefile，无 configure 脽本）
- 编译器: clang 15.0.4 (aarch64-linux)
- 安装产物:
  - `lib/libb64.a` - 静态库
  - `include/b64/cencode.h` - 编码头文件
  - `include/b64/cdecode.h` - 解码头文件
  - `bin/libb64-base64` - 命令行工具

## License
CC-PDDC (Public Domain Dedication and Certification)

## 依赖
无外部依赖

## 注意事项
- libb64 无 `configure` 脽本和 `make install` 目标，需手动安装
- 命令行工具原名 `base64`，与 GNU coreutils `base64` 冲突，已重命名为 `libb64-base64`
- `base64_decode_block` 在解码末尾会多输出一个字节（库的设计行为，非 bug）
