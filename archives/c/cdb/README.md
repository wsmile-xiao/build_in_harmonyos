# cdb

创建和读取常量数据库（CDB 格式）的工具和库（DJB cdb 2025-10-21 维护版）。

## 简介

cdb（constant database）是 Daniel J. Bernstein 设计的快速、可靠、简单的
常量数据库包：写入一次、批量查询，单次查询通常只需两次磁盘访问，查询时间
不随库大小增长。2025-10-21 版是 cdb.cr.yp.to 发布的维护版本，在经典 0.75
基础上新增 `cdb64`（64 位哈希与偏移，支持更大数据库）并现代化了构建与文档。

## 主要特性

- 查询快速且有界：完美哈希 + 定长槽位
- 崩溃安全：写库过程不损坏已有数据
- 读写 API：`cdb.h`（读）/ `cdb_make.h`（写）
- 命令行工具：`cdbmake`、`cdbget`、`cdbdump`、`cdbstats`、`cdbtest`，
  便捷脚本 `cdbmake-12`、`cdbmake-sv`，以及对应的 `cdb64*` 全套
- 零依赖：纯 C，仅 libc

## 与 tinycdb 的区别

仓库已收录 `tinycdb/0.81`（独立实现，MIT）。本包是 DJB 原版血脉的维护版
（公有领域），API 兼容经典 cdb，并额外提供 cdb64 变体与 `num`(long long)
抽象的读 API。二者 CONFLICTS 关系与 pkgsrc 一致（同为 cdb 格式工具）。

## 版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 20251021 | built | 2026-09-07 |
