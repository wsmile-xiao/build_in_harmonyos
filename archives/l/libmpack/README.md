# libmpack

## 简介

libmpack 是一个小巧的二进制序列化/RPC 库，实现了 msgpack 和 msgpack-rpc 规范。它是一个独立的 C89 库，零系统依赖，只使用 C 标准库的 memcpy 函数。

## 特性

- 纯 C89 实现，可移植性强
- 零系统依赖
- 小巧高效（约 2k 行 C 代码）
- 支持 msgpack 和 msgpack-rpc
- 完全增量式/迭代式的解析/序列化 API
- 不需要动态内存分配
- 端序无关，适配大端和小端平台
- 100% 测试覆盖率

## 已编译版本

- **1.0.3** (2026-05-28) - [查看详情](./1.0.3/)
- **1.0.5** (2026-07-15) - [查看详情](./1.0.5/)

## 来源

- GitHub: https://github.com/libmpack/libmpack
- License: MIT

## 相关资源

- [msgpack 规范](https://github.com/msgpack/msgpack/blob/master/spec.md)
- [msgpack-rpc 规范](https://github.com/msgpack-rpc/msgpack-rpc/blob/master/spec.md)