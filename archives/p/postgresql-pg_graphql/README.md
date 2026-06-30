# pg_graphql

> GraphQL support for PostgreSQL — reflect GraphQL schema from SQL schema (Rust/PGRX)

## 简介

pg_graphql 是一个 PostgreSQL 扩展，由 Supabase 开发，为 PostgreSQL 数据库添加 GraphQL 支持。它能够从现有的 SQL schema 自动反射生成 GraphQL schema，并将查询解析完全封装在数据库服务器中。

这意味着任何能连接 PostgreSQL 的编程语言都可以通过 GraphQL 查询数据库，无需额外的服务器、进程或库。pg_graphql 支持 pageable collection 的 Query 类型、批量 insert/update/delete 的 Mutation 类型，以及基于外键的关系定义。

pg_graphql 使用 Rust 语言和 PGRX（PostgreSQL Rust 扩展框架）开发，编译为 PostgreSQL 扩展后以 C 动态库形式加载。

## OHOS 适配要点

- PGRX (Rust) 项目，需要 Cargo 构建工具链和 Rust 编译器
- 需要配置 `.cargo/config.toml` 以适配 OpenHarmony 目标平台（链接器和目标三元组）
- Cargo.lock 和 Cargo.toml 需补丁以使用兼容的依赖版本
- pg_graphql.control 需补丁以设置正确的模块路径
- 共 4 个平台适配补丁

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| PostgreSQL | 17.10 | 核心数据库 |
| Rust | ≥ 1.70 | 编译工具链 |
| PGRX | ≥ 0.11 | PostgreSQL Rust 扩展框架 |

## 功能验证

```sql
CREATE EXTENSION pg_graphql;

-- 查看生成的 GraphQL schema
SELECT graphql.resolve('query { __schema { types { name } } }');
```

## 参考

- [pg_graphql 文档](https://supabase.github.io/pg_graphql/)
- [pg_graphql GitHub](https://github.com/supabase/pg_graphql)