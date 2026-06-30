# postgresql-common

> Perl/shell PostgreSQL cluster manager — create, drop, and manage PG clusters

## 简介

postgresql-common 是 Debian/Ubuntu 系统中 PostgreSQL 集群管理的基础设施包。它提供了一系列 Perl 和 Shell 脚本，用于创建、删除、升级和管理 PostgreSQL 数据库集群（即多个 PostgreSQL 实例和版本的共存管理）。

核心组件包括 `pg_createcluster`、`pg_dropcluster`、`pg_lsclusters`、`pg_ctlcluster` 等命令，以及 `pg_wrapper`——一个版本切换工具，通过 symlinks 让用户可以在多个 PostgreSQL 版本之间无缝切换客户端命令（如 psql、pg_dump）。

postgresql-common 还提供了配置管理工具 `pg_conftool`，支持在线修改 postgresql.conf 和 pg_hba.conf 等配置文件。

## OHOS 适配要点

- postgresql-common 是 Perl/shell 项目，无 configure 步骤，使用简单 Makefile（仅生成 man pages）[E202]
- 安装需手动处理：基于 debian `.install` 文件列表，用 `cp+chmod` 替代 `make install` [E202]
- 需要 12 个平台补丁以适配 OpenHarmony 环境变量和路径差异（所有脚本需修改 shebang 和路径引用）
- `pg_wrapper` 创建 symlinks 替代 PostgreSQL 客户端命令（psql, pg_dump 等）[E200]

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| Perl | ≥ 5.30 | 运行脚本 |

## 功能验证

```bash
# 列出集群
pg_lsclusters

# 创建新集群
pg_createcluster 17 main

# 管理集群状态
pg_ctlcluster 17 main start
pg_ctlcluster 17 main status
```

## 参考

- [postgresql-common GitHub](https://github.com/petere/postgresql-common)
- [Debian PostgreSQL wiki](https://wiki.debian.org/PostgreSQL)