# perl-sql-abstract-pg

PostgreSQL features for SQL::Abstract

## 描述

SQL::Abstract::Pg 扩展了 SQL::Abstract，添加了 PostgreSQL 特有的 SQL 语法支持。该模块被 Mojo::Pg 使用，是 Mojolicious 生态圈的重要组成部分。

## 功能特性

- **ON CONFLICT**: 支持 DO NOTHING、DO UPDATE、upsert 操作（含多列冲突目标和字面 SQL）
- **LIMIT/OFFSET**: 分页查询支持
- **GROUP BY / HAVING**: 聚合查询支持
- **JOIN**: 支持 INNER JOIN、LEFT JOIN、RIGHT JOIN，含多条件 ON 子句
- **FOR UPDATE**: 行级锁支持，含 SKIP LOCKED
- **AS**: 字段别名支持，含字面 SQL 和绑定值
- **JSON**: `-json` 操作符，将 Perl 数据结构编码为 JSON
- **RETURNING**: INSERT 返回值支持

## 版本

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| 1.0 | built | 2026-07-01 |

## 依赖

- SQL::Abstract >= 2.0
- Perl >= 5.016

## 许可证

Artistic License 2.0

## 上游

- CPAN: https://cpan.metacpan.org/authors/id/S/SR/SRI/SQL-Abstract-Pg-1.0.tar.gz
- GitHub: https://github.com/mojolicious/sql-abstract-pg
