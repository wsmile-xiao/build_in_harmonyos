# pg_probackup 2.5.16 编译笔记

## 概述

pg_probackup 2.5.16 是 PostgreSQL 的备份和恢复管理器。使用 PGXS (PostgreSQL Extension Building System) 编译，依赖 PostgreSQL 17 开发环境（pg_config, libpq）。

## 编译环境

- **编译器**: clang 15.0.4
- **构建系统**: PGXS (makefile)
- **依赖**: PostgreSQL 17.10 (预编译包), zlib
- **平台**: OpenHarmony aarch64

## 关键问题与解决方案

### 问题1: PGXS 模式下 srchome 路径错误

**现象**: Makefile 中 `ifdef top_srcdir` 在 PGXS include 之前被评估，导致 `srchome` 被设置为错误路径 `/storage/Users/currentUser/tmp/`，而非 PostgreSQL 源码目录。

**原因**: GNU Make 的 `ifdef` 条件在 parse time 评估。`top_srcdir` 在 PGXS include 之前未定义，导致 `else` 分支将 `top_srcdir=../..`，`srchome` 解析为相对路径的绝对形式。

**解决方案**: 在 `ifdef USE_PGXS` 块中，PGXS include 之后，添加 `PGSRCDIR` 变量指向包含借用文件的 PG 源码目录，并 override `srchome`。

### 问题2: 借用的 PostgreSQL 源文件不可用

**现象**: pg_probackup 借用 PostgreSQL 源文件（pg_crc.c, receivelog.c, streamutil.c, xlogreader.c, instr_time.h, walmethods.c/h），通过符号链接从 PG 源码树获取。但 PGXS 模式下只有预编译的 PG 安装，没有源码树。

**原因**: PGXS Makefile.global 在 PGXS 模式下不设置 `abs_top_srcdir`（只在非 PGXS 模式下设置）。因此无法通过 PGXS 定位 PG 源码目录。

**解决方案**:
1. 从 PostgreSQL 17.10 GitHub 下载需要的源文件
2. 创建目录结构 `~/tmp/pg17_full/src/...` 模拟 PG 源码树
3. 直接复制借用文件到 pg_probackup 的 src/ 目录
4. 移除 Makefile 中的符号链接创建规则
5. 从 EXTRA_CLEAN 中移除借用文件（避免 clean 时删除）

### 问题3: zlib 链接缺失

**现象**: 链接阶段出现 undefined symbol: gzseek, compress2, zError 等 zlib 相关符号。

**原因**: PGXS 的 `PG_LIBS_INTERNAL = $(libpq_pgport)` 不包含 `-lz`。

**解决方案**: 在 Makefile 中添加 `PG_LIBS = -lz`。

### 问题4: NLS 安装失败

**现象**: `make install` 时 po/ru.mo 编译失败（`make: o: No such file or directory`）。

**原因**: nls-global.mk 的 msgfmt 命令在 OpenHarmony 上不工作。

**解决方案**: 手动安装二进制文件到 $DEFAULT_PREFIX/bin/ 和 $TEST_PREFIX/$DEFAULT_PREFIX/bin/，跳过 NLS 安装。NLS 翻译文件（俄语）对核心功能不是必需的。

## 补丁说明

10 个补丁文件：
1. `0001-Makefile.patch` - PGXS 构建适配（srchome 修复、借用文件直接复制、zlib 链接）
2. `0002-0010` - 借用的 PostgreSQL 17.10 源文件（instr_time.h, pg_crc.c, receivelog.c/h, streamutil.c/h, walmethods.c/h, xlogreader.c）

## 编译命令

```bash
cd $BUILD_SRC_DIR
make USE_PGXS=1 -j2
# DESTDIR 安装
mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/bin
cp pg_probackup $TEST_PREFIX/$DEFAULT_PREFIX/bin/
# 本地安装
cp pg_probackup $DEFAULT_PREFIX/bin/
```

## 验证结果

```
pg_probackup 2.5.16 (PostgreSQL 17.10)
```

## 制品文件

- `pg_probackup-2.5.16-ohos-aarch64.tar.gz` (5.88MB)
- `pg_probackup-2.5.16-ohos-aarch64-debug.tar.gz` (1.65MB)
---

**编译结束**: 2026-06-09 21:43
**最终状态**: built
