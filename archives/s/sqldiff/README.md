# sqldiff

**SQLite schema diff 工具** — 比较两个 SQLite 数据库文件，输出将第一个数据库转换为第二个的 SQL 文本。

## 概述

sqldiff 是 SQLite 源码树中的工具（位于 `tool/sqldiff.c`），是一个命令行实用程序：

- 检测两个 SQLite 数据库之间的 schema 差异
- 检测同名表之间的数据（行级）差异
- 输出 SQL 语句（DROP TABLE、CREATE TABLE、ALTER TABLE、INSERT、UPDATE、DELETE）将 DB1 转换为 DB2
- 支持变更集格式输出用于增量同步

## 版本 3.51.3

| 字段 | 值 |
|------|------|
| **源码** | https://sqlite.org/2026/sqlite-src-3510300.zip |
| **许可证** | blessing (https://sqlite.org/copyright.html) |
| **语言** | C |
| **构建系统** | custom（使用 amalgamation 直接 cc 编译） |
| **依赖** | 无（自包含 SQLite 引擎） |
| **状态** | built |

## 用法

```
sqldiff [options] DB1 DB2

选项:
  --changeset FILE      将变更集写入 FILE
  -L|--lib LIBRARY      加载 SQLite 扩展库
  --primarykey          使用 schema 定义的 PRIMARY KEY
  --rbu                 输出 SQL 创建/填充 RBU 表
  --schema              仅显示 schema 差异
  --summary             仅显示差异汇总
  --table TAB           仅显示指定表的差异
  --transaction         在事务内显示 SQL 输出
  --vtab                处理 fts3, fts4, fts5 和 rtree 表
```

## 编译说明

sqldiff 是 SQLite 源码树中的工具。SQLite 源码的 `configure` 需要 tclsh（OHOS 平台不可用），因此采用**直接编译方式**配合 SQLite amalgamation。

### 编译步骤

1. 下载 SQLite 源码: `sqlite-src-3510300.zip`
2. 下载 SQLite amalgamation: `sqlite-amalgamation-3510300.zip`
3. 将 `sqlite3.c`、`sqlite3.h`、`sqlite3ext.h` 从 amalgamation 复制到源码根目录
4. 编译:
   ```
   cc -o sqldiff tool/sqldiff.c sqlite3.c \
       -I. -Itool -Iext/misc \
       -DHAVE_READLINE=0 -DSQLITE_THREADSAFE=0 \
       -fPIC -O2
   ```
5. 安装: `cp sqldiff $PREFIX/bin/sqldiff`

### 关键编译决策

- `-DHAVE_READLINE=0`: OHOS 平台无 readline 库
- `-DSQLITE_THREADSAFE=0`: 单线程模式，最小化依赖
- `-Iext/misc`: `sqldiff.c` 引用了 `sqlite3_stdio.h` 头文件
- 未使用 `configure`: OHOS 平台无 tclsh

## 测试结果

12 个测试用例执行，11 通过，1 部分（变更集对 schema 差异的已知限制）。

关键验证功能:
- ✅ 完整差异（schema + 数据）
- ✅ 仅 schema 差异 (`--schema`)
- ✅ 汇总差异 (`--summary`)
- ✅ 指定表差异 (`--table`)
- ✅ 事务包裹输出 (`--transaction`)
- ✅ 相同数据库检测（无输出）
- ✅ 错误处理（不存在的文件）
- ✅ ELF64 AArch64 PIE 二进制，仅 libc.so 依赖

详见 `3.51.3/reports/test-report.md`。