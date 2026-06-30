# SQLite

## 简介

SQLite 是一个自包含、高可靠性、嵌入式、全功能的 SQL 数据库引擎，广泛应用于移动设备、嵌入式系统和桌面应用程序。

## 功能概述

- **嵌入式数据库**：无需独立服务器进程，直接嵌入应用程序
- **零配置**：无需安装或管理，开箱即用
- **单文件存储**：整个数据库存储在一个跨平台的磁盘文件中
- **ACID 事务**：支持原子性、一致性、隔离性、持久性
- **SQL-92 标准**：支持大部分 SQL-92 标准
- **跨平台**：支持多种操作系统和硬件平台

## OHOS 适配

### 适配要点

1. **HMDFS 限制**：标准 configure 流程在 HMDFS 文件系统上无法创建临时文件，需要使用 `Makefile.fallback` 替代
2. **平台识别**：需要修改 `config.guess` 添加 HarmonyOS 识别支持
3. **系统验证**：需要修改 `config.sub` 添加 OHOS 操作系统支持

### 已知问题

- HMDFS 文件系统不支持在当前目录创建临时文件（`mktemp` 失败）
- 标准 autotools 流程需要修改或使用替代方案

### 与 Linux 的差异

- 使用 `cc` 而非 `gcc` 作为默认编译器
- 需要显式设置 `TMPDIR` 环境变量解决 HMDFS 权限问题

## 排除与替代

无特殊排除项。

## 依赖

### 编译依赖

- 无外部依赖（自包含）
- 可选：zlib（用于压缩功能）

### 运行依赖

- 无外部运行依赖

## 功能验证

```bash
# 版本验证
sqlite3 --version

# 创建测试数据库
sqlite3 test.db "CREATE TABLE test(id INT, name TEXT); INSERT INTO test VALUES(1, 'hello'); SELECT * FROM test;"

# 查询测试
sqlite3 test.db "SELECT sqlite_version();"
```

## 参考

- 官网：https://www.sqlite.org/
- 源码：https://www.sqlite.org/download.html
- 文档：https://www.sqlite.org/docs.html