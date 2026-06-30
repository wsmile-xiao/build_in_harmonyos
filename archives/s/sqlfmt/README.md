# sqlfmt

> Go-based SQL formatter supporting PostgreSQL, SQLite, Oracle and other dialects

## 简介

sqlfmt 是一个用 Go 语言编写的 SQL 格式化工具，主要针对 PostgreSQL、SQLite 和 Oracle 等 DBMS 方言提供格式化支持。它可以格式化 DML（SELECT、INSERT、UPDATE、DELETE）、基本 DDL，以及 PostgreSQL 中语言为 plpgsql 或 sql 的函数和过程。

sqlfmt 支持多种配置选项，包括缩进大小、关键字大小写转换、最大行长度、方言选择等，可通过配置文件、命令行参数或文件内指令进行定制。

## OHOS 适配要点

- **⚠️ 编译失败**：Go linker 使用 `mmap()` 创建输出 ELF 文件，OpenHarmony HMDFS 不支持此操作，导致 sqlfmt v2025.01.30 无法在 HMDFS 上编译 [E051]
- sqlfmt 没有官方预编译 arm64 二进制文件，GitHub releases 仅提供源码 tarball/zip [P18]
- 需要完整的 Go 工具链（Go ≥ 1.21），编译命令为 `go build -trimpath -ldflags='-s -w' ./cmd/sqlfmt.go`

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| Go | 1.25.7 | 编译工具链 |

## 功能验证

```bash
# 正常情况下（非 HMDFS 环境）的验证
./sqlfmt -d postgresql -i input.sql -o output.sql
./sqlfmt -h  # 查看帮助信息
```

> ⚠️ 注意：当前版本 2025.01.30 在 HMDFS 上因 Go linker mmap 限制无法编译，功能验证暂不可用。

## 参考

- [sqlfmt GitHub](https://github.com/gsiems/sqlfmt)
- [sqlfmt 配置文档](https://github.com/gsiems/sqlfmt#configuration)