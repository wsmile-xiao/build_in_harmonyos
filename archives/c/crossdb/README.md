# CrossDB

CrossDB 是一个用 C 写的超轻量嵌入式 / 服务器 OLTP 关系型数据库：单文件
`src/crossdb.c` 以 amalgamation 方式 `#include` 全部子系统，产出
`libcrossdb` 与交互式客户端 `xdb-cli`，支持内存库与 mmap 文件库、
事务、索引、触发器、pub/sub 以及简化 SQL 方言。

## 功能概述

- 嵌入式（`xdb_open()` 进程内直连）与服务器（`xdb_connect()`，默认 7777 端口）两种形态
- DDL / DML / 聚合 / `ORDER BY` / `LIKE` / `REGEXP` / 分页 / 事务（commit、rollback）
- HASH 与 RBTREE 索引、外键、系统表（`columns` / `tables` / `indexes` / `databases` / `subscriptions`）
- 内存库（`ENGINE=MEMORY`）与 mmap 文件库两种存储后端

## 依赖关系

- 编译依赖：CMake ≥ 3.10（或裸 Makefile）、C 编译器、`pthread`、`dl`
- 运行依赖：无（零第三方库依赖）
- 上游测试：`test/`（`utest.h` 头文件式框架，无外部测试依赖）

## HarmonyOS PC 适配要点

- **plain char 在 AArch64 上是无符号的**：`xdb_stmt_tbl_t.pkey_idx` 的 `-1`
  「尚无主键」哨兵被存成 255，导致每个带 `PRIMARY KEY` 的 `CREATE TABLE`
  都触发 `Duplicate PRIMARY KEY` —— 已改成 `signed char`。
- **musl 没有 `REG_STARTEND`**：`REGEXP` 的被匹配串是带长度前缀的切片、
  并非 NUL 结尾，已改为先复制成 NUL 结尾再 `regexec`。
- **musl 没有 glibc 风格的 `qsort_r`**：`ORDER BY` 走线程局部上下文的
  本地 shim，委托标准 `qsort`。
- **HMDFS / tmpfs 拒绝 `posix_fallocate`（EACCES）**：扩文件回退到
  `ftruncate`（与上游 `__APPLE__` 分支同样的做法）。
- **`getopt()` 返回 `int`**：`xdb-cli` 原先用 `char ch` 接收，在无符号
  `char` 平台上循环永不终止；另补了 `--version` / `--help` 长选项以通过
  平台 L2 冒烟门禁。
- 上游 `test/` 冒烟套件经 CMake `XDB_BUILD_TESTS`（默认 OFF）接入 CTest，
  配方 `build()` 中以 `ctest --verbose` 真实执行。

## 参考资料

- 官网：https://crossdb.org
- 源码仓库：https://github.com/crossdb-org/crossdb
