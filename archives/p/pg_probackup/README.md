# pg_probackup

pg_probackup 是 PostgreSQL 的备份和恢复管理工具，由 PostgresPro 开发。

## 功能概述

- 支持全量、增量、归档备份
- 提供备份验证和恢复功能
- 支持备份压缩和并行处理
- 集成 PostgreSQL 的 WAL 归档机制

## OHOS 适配

- **构建系统**: PGXS (PostgreSQL Extension Building Infrastructure)
- **主要补丁**: Makefile PGXS 适配 + 多个 PG 源码文件的 HarmonyOS 平台修复
- **编译要点**: PGXS 构建需要复制 PG 源码文件（软链接在预编译 PG 下不工作），PG_LIBS 需添加 -lz

## 依赖关系

- PostgreSQL (17.10)
- zlib (1.3.1)

## 参考资料

- 官网: https://github.com/postgrespro/pg_probackup