# plpgsql_check

> PL/pgSQL static checker and profiler extension for PostgreSQL

## 简介

plpgsql_check 是一个 PostgreSQL 扩展，为 PL/pgSQL 函数和过程提供静态检查和性能分析功能。它可以在函数创建或修改时检测语法错误、未使用的变量、类型不匹配、缺失的 RETURN 等问题，帮助开发者在运行前发现潜在错误。

plpgsql_check 还提供性能分析（profiling）功能，可以记录 PL/pgSQL 函数中每条语句的执行次数和耗时，帮助定位性能瓶颈。

该扩展由 Pavel Stehule（okbob）开发，是 PostgreSQL 开发和调试的重要工具，特别是在复杂的存储过程和函数开发场景中。

## OHOS 适配要点

- 使用 PostgreSQL Makefile 构建系统，依赖 `pg_config` 获取编译参数
- 编译命令：`make` 和 `make install`（需设置正确的 pg_config 路径）

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| PostgreSQL | 17.10 | 核心数据库 |

## 功能验证

```sql
CREATE EXTENSION plpgsql_check;

-- 检查函数
SELECT plpgsql_check_function('my_function()');

-- 启用性能分析
SET plpgsql_check.profiler = true;
```

## 参考

- [plpgsql_check GitHub](https://github.com/okbob/plpgsql_check)
- [plpgsql_check 文档](https://github.com/okbob/plpgsql_check#documentation)