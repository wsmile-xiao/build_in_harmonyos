# raft

## 简介

Raft 是 Raft 共识协议的 C 语言实现，用于构建分布式系统。它是 dqlite 和 cowsql 的核心依赖。

## 特性

- 完整的 Raft 共识协议实现
- 支持多种传输方式（UV、TCP）
- 领导者选举和日志复制
- 快速恢复和故障处理
- LGPL-3.0 许可证（含例外条款）

## OHOS 适配

### 关键适配点

- **UV 传输**: 需要 libuv >= 1.18.0 支持
- **PKG_CONFIG_PATH**: 编译时必须设置 PKG_CONFIG_PATH 以找到 libuv

### 编译验证

```bash
pkg-config --modversion raft
# 输出: 0.22.1
```

检查 UV 支持：
```bash
ls ~/usr/local/include/raft/uv.h
# 必须存在此文件
```

## 依赖

### 运行时依赖
- libuv >= 1.18.0（UV 传输需要）

### 编译时依赖
- libuv 开发库（pkg-config）

## 使用方式

```c
#include <raft.h>
#include <raft/uv.h>  // UV transport

raft_uv_init(&transport, &loop, &config);
```

## 参考

- 源码: https://github.com/cowsql/raft
- 文档: https://github.com/cowsql/raft/blob/main/README.md