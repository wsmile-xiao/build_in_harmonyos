# tdb — Samba trivial database

## 概述

tdb（Trivial Database）是 Samba 项目的轻量级嵌入式键值数据库库（LGPL-3.0-or-later），
单文件、支持多进程并发读写与内部锁，广泛用于 Samba 生态（tdb/talloc/ldb/tevent）。

**本仓库适配版本**：1.4.15（HarmonyOS PC aarch64 / musl）

## 功能概述

- C 库 `libtdb`：键值存储、事务、遍历、备份/恢复 API（`tdb_open`/`tdb_store`/`tdb_fetch`/…）
- 命令行工具：`tdbtool`、`tdbdump`、`tdbbackup`、`tdbrestore`
- 可选 python 绑定（`pytdb`，本包未启用）

## OHOS 适配要点

1. **构建系统为 Samba waf（wafsamba）**：非主流 autotools/cmake。构建通过
   `PYTHON=python3 ./configure && make` 驱动内置 waf（`buildtools/bin/waf`）。
   详细范式见本仓库知识草稿与版本级 notes。
2. **`/tmp` 只读 + HMDFS 权限归一化**：`lib/replace` 的 `HAVE_SECURE_MKSTEMP`
   运行探针在鸿蒙必失败（探针硬编码 `/tmp`，且 HMDFS 将文件权限归一化为 0640，
   0600 断言不可满足），上游标为 `mandatory=True` 会直接中断 configure。
   补丁 0001 将其改为非致命，使用 lib/replace 内置 mkstemp 替代实现。
3. **musl 无 robust mutex**：`pthread_mutexattr_setrobust` 未声明；
   configure 自动探测关闭 `USE_TDB_MUTEX_LOCKING`（无需显式传
   `--disable-tdb-mutex-locking`），37 个单测在无 robust mutex 模式下全部通过。
4. **python 绑定未启用**：平台 `python3-config --embed` 输出含平台不存在的
   `-lintl`，pyembed 探针无法链接；本包以 `--disable-python` 构建纯 C 库。
   补丁 0002 让 `make test` 在禁用 python 时显式跳过 python 测试（否则误跑必失败）。

## 依赖关系

- 编译依赖：无外部库（`lib/replace` 内置于源码包）；构建期需要 `python3`（驱动 waf）
- 运行依赖：无（系统 libc/ld）

## 参考资料

- 上游官网：https://tdb.samba.org/
- 源码发布：https://download.samba.org/pub/tdb/
- 本仓库版本笔记：`1.4.15/notes.md`
