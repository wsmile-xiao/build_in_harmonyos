# postgresql-bdr-extension

BDR (Bi-Directional Replication) 扩展，为 PostgreSQL 提供多主复制功能。

## 版本

- 1.0 (built, 2026-06-09)

## 构建说明

使用 autotools 构建系统。需要 bash 执行 configure（sh 下 heredoc 有 HMDFS 权限问题）。

关键适配补丁：
- 0001-configure.patch: HMDFS umask 077 → 022 修复

## 依赖

postgresql-bdr 9.4.13
