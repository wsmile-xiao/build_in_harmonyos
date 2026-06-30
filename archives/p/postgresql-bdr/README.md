# postgresql-bdr

PostgreSQL BDR (Bi-Directional Replication) 是 PostgreSQL 的多主复制扩展版本。

## 版本

- 9.4.13 (built, 2026-06-09)

## 构建说明

postgresql-bdr 使用 autotools 构建系统（基于 PostgreSQL 9.4）。

关键适配补丁：
- 0003-config-config.guess.patch: HarmonyOS 平台识别
- 0004-config-config.sub.patch: linux-ohos 内核组合支持
- 0006-src-include-c.h.patch: stdbool.h 兼容修复（bool类型冲突）
- 0007-src-include-pg_config.h.patch: DLSUFFIX 定义

## 依赖

openssl, zlib
