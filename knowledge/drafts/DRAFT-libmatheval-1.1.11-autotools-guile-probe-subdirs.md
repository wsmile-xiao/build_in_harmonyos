# DRAFT-libmatheval-1.1.11-autotools-guile-probe-subdirs

> Contributor: 2301_76770579 | Status: Draft | Updated: 2026-09-08
> Source: libmatheval 1.1.11 HarmonyOS PC 适配（GNU autotools，从零写配方）

## 现象（三类移植坑合一）

libmatheval 1.1.11（2013-08 发布，自带生成 `configure` + libtool）迁到
OHOS aarch64（musl 工具链）时，连中三类**结构性**问题，彼此独立、可单点演示：

| # | 坑 | 直接现象 |
|---|---|---|
| 1 | 包内 2013 `config.guess` 的 mktemp 探针在 HMFS 写 dummy.c 被拒 | `unable to guess system type`；同年 `config.sub` 只认 `linux-gnu`，**不认 `-musl`**：`sh config/config.sub aarch64-unknown-linux-musl` → `Invalid configuration` |
| 2 | `configure.in` **无条件** `GUILE_FLAGS`，其 `guile-config` 探针缺失即致命 | `configure: error: guile-config required but not found`（guile 对核心库纯属可选，无 `--without-guile`） |
| 3 | 顶层 `SUBDIRS = doc lib tests`：`doc` 需 makeinfo；`tests/matheval.c` 是 **guile 扩展**（`#include <libguile.h>`，用 guile 1.8/2.0 已移除的 `scm_sizet/scm_makfrom0str`…） | `make`/`make check` 在 tests 编译即失败；guile 2.2（本仓已适配版）API 不兼容，套件**不可运行** |

## 修复组合拳（三者都是配方侧、非改上游源）

1. **跳过 config.guess + 兼容 config.sub**：显式 `--build/--host=aarch64-unknown-linux-gnu`
   （config.sub 认得的拼写）。build==host → 原生模式，conftest 可直接运行；config.guess
   完全不执行（纯 shell 的 config.sub 只校验给定三元组、不落盘）。
2. **空探针 stub 顶掉硬性 -config**：写一个 `compile`/`link` 都只 `exit 0`、无输出的脚本，
   经 `GUILE_CONFIG`/`GUILE_TOOLS` 环境变量预置给 configure → `GUILE_CFLAGS/LDFLAGS`
   被置空，探针走 cache/env 分支不再 PATH 搜索。核心库编译期完全不碰 guile。
3. **SUBDIRS 运行期裁剪**：`make SUBDIRS=lib` 只编库子目录；`make SUBDIRS=lib install`
   只装库+头；顶层 `libmatheval.pc` 是 pkgconfig_DATA，单独 `make install-pkgconfigDATA`。
   顺带按仓内惯例把 `configure` 的 `umask 077 → 022`（HMFS 归档成员权限）。

## 上游正确性套件处理（诚实报告）

上游 `make check` 是 autotest，驱动 `tests/matheval` 把 libmatheval 包成 guile 扩展再由
`.at` 脚本驱动。该驱动无条件 `#include <libguile.h>` 且用 guile 1.8/2.0 已删 API，在
本目标无法编译 → **上游套件未运行，配方不谎称通过**。替代：test_package 用纯 C 公开 API
逐条复现 `tests/*.at` 数值 oracle（同一表达式、同一期望值、15 位有效数字），共 60 项
断言真机实跑作为 L1 门禁。

## 验证证据

- `sh config/config.sub aarch64-unknown-linux-musl` → `Invalid`；`...-linux-gnu` → 通过。
- `grep -n 'guile-config required' configure` → 命中（致命探针在）。
- conan create（OHOS aarch64 CI）内嵌 test_package C-API oracle 实跑 **60/60**。

## 作用域与维护条件

- 作用域：配方级移植（configure 参数 + 环境 + make 目标选择），不动上游任何源码。
- 上游若修 config.sub（支持 musl）或提供 `--without-guile`，可简化但配方仍成立。
- 禁忌：不得谎报上游 make check 结果；不得硬写 2013 config.sub 不认的 `-musl` 三元组；
  不得 sed 永久改源树 Makefile.in 来裁剪 SUBDIRS（用 make 变量覆盖即可）。
