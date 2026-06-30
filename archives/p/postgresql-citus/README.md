# Citus

> Distributed PostgreSQL extension — transforms Postgres into a distributed database

## 简介

Citus 是一个 PostgreSQL 扩展，将单机 PostgreSQL 转变为分布式数据库。它通过分片（shard）将数据分布到多个 PostgreSQL 节点上，提供了分布式表、引用表和列式存储等核心能力。

Citus 支持 SELECT、INSERT、UPDATE、DELETE 等操作的分布式执行，包括 WHERE 子句下推、JOIN 下推、聚合下推等优化。它特别适合多租户 SaaS 应用、实时分析仪表板和时序数据处理等场景。

作为 PostgreSQL 扩展，Citus 可以与最新的 PostgreSQL 版本配合使用，并且与 PostGIS、HyperLogLog 等其他 PostgreSQL 扩展无缝协作。

## OHOS 适配要点

- config.guess 需要 HarmonyOS 识别补丁（aarch64-unknown-linux-ohos）[E007]
- config.status 在 HMDFS 上因 mktemp 问题失败，需指定固定临时目录 [E011]
- 需要 cpp (C preprocessor) wrapper，使用 `clang -E` 替代 [E200]
- `SHELL=bash` 必须设置，避免 musl sh heredoc 问题 [E200]
- lz4 依赖通过 cmd-pkgs 预编译包（1.10.0）解决 [P18]

## 排除与替代

| 排除组件 | 替代方案 | 说明 |
|----------|----------|------|
| 内嵌 lz4 | 系统 lz4 1.10.0 | Citus 源码内嵌 lz4，应使用 cmd-pkgs 预编译版本 |

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| PostgreSQL | 17.10 | 核心数据库 |
| lz4 | 1.10.0 | 压缩库 |
| zstd | — | 压缩库 |
| curl | — | HTTP 客户端 |

## 功能验证

```sql
CREATE EXTENSION citus;
SELECT create_distributed_table('events', 'device_id');
SELECT * FROM events WHERE device_id = 1 LIMIT 5;
```

## 参考

- [Citus 文档](https://docs.citusdata.com/en/stable/)
- [Citus GitHub](https://github.com/citusdata/citus)