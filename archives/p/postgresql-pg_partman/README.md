# pg_partman

> Partition management extension for PostgreSQL — time and ID based partitioning

## 简介

pg_partman 是一个 PostgreSQL 扩展，用于简化基于时间或 ID/数值的表分区管理。它支持声明式分区（范围分区和列表分区），并提供自动创建和维护子分区的能力。

pg_partman v5.x（当前版本 5.4.3）要求 PostgreSQL ≥ 14，不再支持触发器式分区，所有分区均使用内置声明式分区机制。它提供后台工作进程（BGW）用于自动维护，也可通过 `run_maintenance()` 函数手动触发。

核心功能包括：分区创建与维护、默认分区管理、子分区支持、保留策略（自动删除旧分区）、约束排除优化等。

## OHOS 适配要点

- PGXS 扩展使用 `make USE_PGXS=1` 编译 [E200]
- pg_partman 是纯 SQL/PL/pgSQL 扩展，C 编译量极少，适配难度低
- 如需使用后台工作进程（BGW），需在 `shared_preload_libraries` 中添加 `pg_partman_bgw`

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| PostgreSQL | 17.10 | 核心数据库 |
| PL/pgSQL | 内置 | 扩展逻辑实现 |

## 功能验证

```sql
CREATE EXTENSION pg_partman;

-- 创建基于时间的分区
SELECT partman.create_partition('public.events', 'event_time', '1 day');

-- 运行维护
SELECT partman.run_maintenance();
```

## 参考

- [pg_partman 文档](https://github.com/pgpartman/pg_partman/blob/master/doc/pg_partman.md)
- [pg_partman GitHub](https://github.com/pgpartman/pg_partman)