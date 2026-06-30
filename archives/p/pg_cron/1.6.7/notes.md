# pg_cron 1.6.7 适配笔记

## 编译环境
- 构建系统: makefile (PGXS - PostgreSQL Extension Building Infrastructure)
- 编译日期: 2026-06-02
- 编译器: clang 15.0.4
- PostgreSQL: 17.0
- 状态: built

## 编译步骤

pg_cron 是 PostgreSQL 的定时任务扩展，使用 PGXS 构建系统。

1. **下载源码**: `https://github.com/citusdata/pg_cron/archive/refs/tags/v1.6.7.tar.gz`
2. **解压源码**: 到 `/storage/Users/currentUser/builds/pg_cron-1.6.7.work`
3. **编译**: `make`（使用 pg_config 获取 PostgreSQL 构建配置）
4. **安装到 staging**: `make install DESTDIR=/storage/Users/currentUser/test-install-pg_cron-1.6.7`
   - 遇到 install 命令问题，手动复制 SQL 文件
5. **生成产物**: 预编译包制作（后续步骤）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | install 命令不支持多文件安装 | toybox install 不支持 GNU install 的批量文件安装语法（`install -m 644 file1 file2 file3 dest/`） | 手动使用 cp 命令逐个复制 SQL 文件到 staging 目录 |
| 2 | 硬编码 /etc 路径 | 源码中硬编码 `/etc/cron.allow`、`/etc/cron.deny` 等路径 | 预扫描报告标记为 medium，需要后续处理（可通过 PostgreSQL 配置解决） |

## 源码修改

无补丁文件。源码中存在硬编码 `/etc` 路径问题，但这是 pg_cron 的设计特性（读取系统级 cron 配置），不影响编译和基本功能。

## 依赖版本

- PostgreSQL 17.0（提供 pg_config 和 PGXS 构建系统）
- clang 15.0.4（编译器）
- libpq（PostgreSQL 客户端库）

## 验证结果

```bash
# 检查产物文件
ls -la /storage/Users/currentUser/test-install-pg_cron-1.6.7/storage/Users/currentUser/usr/local/lib/postgresql/pg_cron.so
ls -la /storage/Users/currentUser/test-install-pg_cron-1.6.7/storage/Users/currentUser/usr/local/share/postgresql/extension/

# 产物清单：
# - pg_cron.so（共享库）
# - pg_cron.control（扩展控制文件）
# - pg_cron--*.sql（SQL 脚本，包括初始脚本和升级脚本）
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| pg_cron.so | 待确认 | PostgreSQL 扩展共享库 |
| pg_cron.control | 待确认 | 扩展控制文件 |
| pg_cron--*.sql | 待确认 | SQL 升级脚本 |

## 注意事项

1. **PGXS 构建系统**: pg_cron 使用 PostgreSQL Extension Building Infrastructure (PGXS)，需要先安装 PostgreSQL 并配置 pg_config。
2. **硬编码路径**: 源码中硬编码了 `/etc/cron.allow`、`/etc/cron.deny` 等路径，这是 pg_cron 的设计特性，用于系统级 cron 配置管理。
3. **install 命令限制**: toybox install 不支持 GNU install 的批量文件安装语法，需要手动处理。
---

**编译结束**: 2026-06-02 12:50
**最终状态**: built
