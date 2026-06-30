# postgresql-sequential-uuids 1.0.3 for HarmonyOS

## 概述

postgresql-sequential-uuids 在 HarmonyOS/OpenHarmony (aarch64) 上的编译指南和测试记录。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | postgresql-sequential-uuids |
| 版本 | 1.0.3 |
| 下载地址 | https://github.com/tvondra/sequential-uuids |
| 官方文档 | https://github.com/tvondra/sequential-uuids |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS HongMeng Kernel 1.11.0 |
| 架构 | aarch64 |
| 编译器 | clang (LLVM) |
| 构建系统 | PGXS |

## 编译步骤

```bash
# 1. 下载源码
git clone https://github.com/tvondra/sequential-uuids.git
cd sequential-uuids
git checkout 1.0.3

# 2. 配置环境
source /path/to/postgresql/setup.env

# 3. 编译
make USE_PGXS=1

# 4. 安装
make USE_PGXS=1 install
```

## 遇到的问题

### 问题1: PGXS 构建系统适配

**现象**: 使用 PGXS 构建系统，无需 configure 步骤

**原因**: PostgreSQL 扩展使用 PGXS 构建系统

**解决**: 直接使用 make USE_PGXS=1 进行编译

## 测试结果

详见 [test-report.md](./reports/test-report.md)

| 测试项 | 结果 |
|--------|------|
| 编译 | ✅ |
| 安装 | ✅ |
| 功能测试 | ✅ |

## 验证安装

```bash
# 检查安装
ls -la $HOME/usr/local/lib/postgresql/sequential_uuids*

# 检查功能
psql -c "CREATE EXTENSION sequential_uuids;"
psql -c "SELECT uuid_sequence_nextval(1);"
```

## 经验总结

1. postgresql-sequential-uuids 1.0.3 使用 PGXS 构建系统
2. PGXS 无需 configure 步骤
3. 依赖 PostgreSQL 17.0+

## 参考资料

- GitHub: https://github.com/tvondra/sequential-uuids