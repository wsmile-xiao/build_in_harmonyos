# TimescaleDB 2.27.2 编译笔记

## 概述
TimescaleDB 是 PostgreSQL 的时序数据库扩展，用于高性能实时分析。

## 编译环境
- PostgreSQL: 17.0
- Compiler: clang 15.0.4
- Build System: CMake

## 遇到的问题

### 1. PostgreSQL 版本不兼容
TimescaleDB 2.27.2 要求 PostgreSQL 17.2+ (PG_VERSION_NUM >= 170002)，而当前安装的是 PostgreSQL 17.0。

**解决方案**: 使用 EXPERIMENTAL=ON cmake 选项绕过版本检查。

### 2. OpenSSL 头文件路径缺失
编译时找不到 openssl/err.h 头文件。

**原因**: CMakeLists.txt 没有使用 pg_config 提供的 CPPFLAGS（包含 OpenSSL include 路径）。

**解决方案**: 修改 CMakeLists.txt，从 PG_CPPFLAGS 中提取 -I 路径并添加到 include_directories。

### 3. PostgreSQL API 不兼容
PG17.0 缺少 `ri_needLockTagTuple` 成员和 `InplaceUpdateTupleLock` 常量。

**原因**: 这些 API 是 PG17.1+ 引入的。

**解决方案**: 修改 modify_hypertable_exec.c，添加 `#if PG_VERSION_NUM >= 170001` 条件检查。

## 修改的文件
1. src/compat/compat.h - EXPERIMENTAL 版本检查
2. CMakeLists.txt - OpenSSL include 路径
3. src/nodes/modify_hypertable_exec.c - PG17 API 兼容性

## 安装验证
- timescaledb-2.27.2.so: 已安装
- timescaledb-tsl-2.27.2.so: 已安装
- timescaledb.so: 已安装（软链接）
- SQL 脚本文件: 61 个
---

**编译结束**: 2026-06-03 15:24
**最终状态**: built
