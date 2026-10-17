# yudit

## 简介

Yudit 是 Gaspar Sinai 开发的 **X Window 系统上的 Unicode 文本编辑器**，GPL-2.0。
它不依赖本地化环境或 Unicode 字体，自带 TrueType/OTF/CFF 光栅器与内码转换引擎，
支持多语言混排、双向文本与自定义键盘映射。源码包除编辑器本体外还提供三个命令行工具：

| 工具 | 用途 |
|---|---|
| `yudit` | X11 图形编辑器本体 |
| `uniconv` | 字符集转换器（utf-8/utf-16/euc-jp/shift-jis/gb-18030/… 及外部 `.my` 映射） |
| `uniprint` | 把文本排版为 PostScript 打印 |
| `mytool` | 键盘映射（`.kmap`）/编码映射（`.my`）编译工具 |

- 官网 / 发布页：<https://yudit.org/>、<https://yudit.org/download/>
- 许可：GPL-2.0-only（`COPYING.TXT`）

## 构建系统

上游使用**手写的 autoconf 变体**：autoconf 生成的 `configure` + 手写 `Makefile.in` /
`Makefile.conf.in` + 每个子目录一个手写 Makefile（`stoolkit`、`swindow`、`swidget`、
`addon`、`gui`、`mytool`、`uniconv`、`uniprint`），**不是 automake**，也没有
`make check` 目标。

## OHOS 适配

- **构建系统**：autotools（手写变体）；X11 搜索路径需通过 `CPPFLAGS`/`LDFLAGS`
  注入（`configure` 不使用 pkg-config）
- **依赖链**：`libx11/1.8.13`（唯一外部库，`configure.ac AC_PATH_XTRA` / `-lX11`）
  → `xorgproto/2025.1`（显式 require，提供 `X11/X.h`）、`libxcb/1.17.0`、
  `libxau/1.0.11`、`libxdmcp/1.1.5`、`xtrans/1.4.0`、`xcb-proto/1.17.0`（传递）
- **补丁**（3 个，全部为平台可移植性修复，见 `3.1.0/patches/`）：
  - `0001-Makefile.conf.in.patch`：安装时不 strip（OhOS ELF 签名要求，strip 后二进制不可执行）
  - `0002-configure.patch`：HMDFS `umask 077` 临时目录不可写 → `umask 022`；
    硬编码 `/tmp` → `${TMPDIR:-/tmp}`
  - `0003-configure.ac.patch`：与 `0002` 的 `/tmp` 修复同步
- **上游测试**：上游无自动化测试套件；22 个上游 Unicode/PostScript 样例
  （`tests/testtext/*.txt` 19 个 + `tests/{nam,yuu,z}.txt` 3 个）已全量跑通（22/22 PASS）
- 详见 `3.1.0/notes.md`、`3.1.0/reports/test-report.md`

## 版本

| 版本 | 状态 | 编译日期 | 说明 |
|---|---|---|---|
| 3.1.0 | built | 2026-09-22 | 首次 OHOS 适配（3 个平台补丁） |
