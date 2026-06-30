# dqlite

## 简介

dqlite 是 Canonical 开发的分布式 SQLite 库，提供高可用性的 SQLite 集群解决方案。它将 SQLite 扩展为分布式数据库，支持多节点复制和自动故障转移。

## 特性

- 分布式 SQLite 复制
- Raft 一致性算法
- 自动故障转移
- 高可用性集群
- C 语言实现，性能优异
- Apache 2.0 许可证

## 编译信息

- 最新版本: 1.18.6
- 构建系统: autotools
- 编译状态: built
- 编译日期: 2026-05-29

## 依赖

- libuv >= 1.34.0（必需）

## 使用方式

```c
#include <dqlite.h>

// 初始化 dqlite 节点
dqlite_node *node;
int rv = dqlite_node_create(1, "node1", "/data/dqlite", &node);

// 启动节点
rv = dqlite_node_start(node);

// 停止并清理
dqlite_node_stop(node);
dqlite_node_destroy(node);
```

## 已编译版本

| 版本 | 状态 | 日期 | 产物 |
|------|------|------|------|
| 1.18.6 | built | 2026-05-29 | dqlite-1.18.6-ohos-aarch64.tar.gz |

## 平台适配说明

- musl libc 不支持 GNU 扩展 `qsort_r`，已添加兼容实现
- 测试套件因 noreturn 函数问题跳过，需进一步修复测试代码