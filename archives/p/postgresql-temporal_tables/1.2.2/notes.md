# postgresql-temporal_tables 1.2.2 编译笔记

## 编译环境

- **目标平台**: HarmonyOS NEXT (musl libc)
- **编译日期**: 2026-06-04
- **构建系统**: PGXS
- **编译器**: clang 15.0.4

## 依赖版本

| 依赖 | 版本 | 路径 |
|------|------|------|
| PostgreSQL | 17.0 | ~/usr/local/bin/pg_config |

## 编译步骤

### Phase 1: 下载源码

```bash
wget https://github.com/mlt/temporal_tables/archive/refs/tags/v1.2.2.tar.gz
tar -xzf v1.2.2.tar.gz
cd temporal_tables-1.2.2
```

### Phase 2: 编译

```bash
make PG_CONFIG=/storage/Users/currentUser/usr/local/bin/pg_config
```

### Phase 3: 安装

```bash
make install PG_CONFIG=/storage/Users/currentUser/usr/local/bin/pg_config
```

## 问题与方案

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| G0验证失败 | PGXS无configure | 记录为PGXS特性 |
| G4失败 | 扩展无独立二进制 | 预期行为 |

## 产物清单

- temporal_tables.so - PostgreSQL扩展模块

## 安装验证

```bash
# 检查产物文件
ls -lh ~/usr/local/lib/postgresql/temporal_tables.so
ls -lh ~/usr/local/share/postgresql/extension/temporal_tables*

# 产物清单：
# - temporal_tables.so (34K) - 共享库
# - temporal_tables.control - 扩展控制文件
# - temporal_tables--1.2.2.sql - SQL脚本
# - temporal_tables--*.sql - 版本升级脚本
```

## 注意事项

1. **PGXS 构建系统**: temporal_tables 使用 PostgreSQL Extension Building Infrastructure (PGXS)，需要先安装 PostgreSQL 并配置 pg_config。
2. **SQL:2011 标准**: 时态表功能支持 SQL:2011 标准的系统周期时态表。
3. **依赖 PostgreSQL**: 需要 PostgreSQL 17.0 或更高版本。

---
**编译结束**: 2026-06-04
**最终状态**: built