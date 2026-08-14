# alliance 5.1.1 适配笔记（HarmonyOS / OpenHarmony PC aarch64）

## 概述

Alliance VLSI CAD Tools（LIP6）是以 C 为主的 VLSI EDA 工具链。本适配构建其**核心库**：
Mut(mbk)、Rds、Abl、Bdd、Fsm、Fvh，静态库形式（符合 R26）。

- 上游：https://github.com/lip6/alliance （tag v5.1.1）
- 许可证：工具 GPL-2.0-or-later / 库 LGPL-2.0-or-later（COPYING-2.0 + COPYING.LIB-2.0）
- 源码 SHA-256：`7f6a380232911920887b15310b0d48717ec3d77a6247dd3feffb84f7d8cd4682`

## 构建系统

分散式 Autotools：71 个 `configure.in`（旧式 `.in` 后缀）+ 231 个 `Makefile.am`，
由顶层 `autostuff` 脚本与 `alliance.m4`（AM_ALLIANCE 宏）驱动。v5.1.1 GitHub tag
archive 为**裸源码**（无预生成 configure/Makefile.in/ltmain.sh），必须现场自举。

## 鸿蒙适配要点

1. **工具链**：设备 autoconf 2.72 / automake 1.18 / libtool 2.5.4（ohpcd tool_requires），
   flex 2.6.4 / bison 3.8.2 为设备原生工具。
2. **configure.in 现代化**（build() 内 Python 转换，ISO-8859 编码读写）：
   - `AC_INIT(单参)` → `AC_INIT([name], [ver])`
   - `AM_INIT_AUTOMAKE(name, ver)` → `AM_INIT_AUTOMAKE([foreign])`
   - `AM_PROG_LIBTOOL` → `LT_INIT`
   - `alliance.m4` 移除已废弃的 `AC_ENABLE_SHARED`
3. **HMDFS**：config.status 临时目录 umask 077 → `sed` 改为 000（同 afuse E114）；
   `CONFIG_SHELL=/bin/sh`（bash getcwd 缺陷）；`make -j1`（无 jobserver）。
4. **裁剪**：7 个 GUI 工具（dreal/graal/xfsm/xgra/xpat/xsch/xvpn）依赖 X11/Motif，
   鸿蒙无 X11，不构建。
5. **源码获取**：github 从设备不可达，conandata url 列表回退 `file://` 本地副本
   （/storage/Users/currentUser/tmp/alliance-5.1.1.tar.gz）。

## 测试

上游无统一测试套件（无 tests/、无 make check）；仅 ctp/ftl 少量 TESTS（本轮未构建）。
测试以 test_package 消费者测试为准：调用 Mut 核心 API（chain_list 操作、mbkalloc/mbkfree）。

## 已知限制

- 本轮仅核心库；CLI 工具（alcban/asimut/boog/druc/genlib 等）与 GUI 工具后续轮次扩展。
- `alliance.m4` 硬编码 `ALLIANCE_VERSION "5.0"`（上游遗留，与 5.1.1 不符，未改动上游语义）。
- 上游无正式测试框架，PR 报告"上游测试用例"按 N/A（未运行）处理。
