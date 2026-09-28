# pspg 5.8.16 — 适配工作笔记（Windows 阶段 1，2026-09-26）

任务：ohpcd 平台 pspg 5.8.16 · 分支 `feat/pspg-5.8.16`（以平台实际显示为
准，提交前核对绑定与截止时间）。

## W0 依赖分析

直接依赖（制品仓均已归档，MateBook 第一步用 `conan download` 复核二进制
包，R35，禁用 `conan list`）：

| 依赖 | 版本 | 依据 |
|------|------|------|
| ncurses | 6.6 | configure.ac `AX_WITH_CURSES`（无则 configure 报错）+ `AX_WITH_CURSES_PANEL`（需 panelw）；ncurses/6.6 单组件包提供 panelw/menuw/formw 与 ncursesw.pc |
| readline | 8.3 | configure.ac `AX_LIB_READLINE`（上游可选：未命中则无 HAVE_LIBREADLINE，pspg 仍可用）；require 以保留完整搜索/历史功能 |

可选依赖（不 require）：PostgreSQL（AX_LIB_POSTGRESQL 未命中仅 NOTICE，
configure.ac 显式处理）；clock_gettime 由 musl libc 提供（AC_SEARCH_LIBS
命中默认分支）。
构建工具：无 bootstrap 需求（configure 预生成），无 libtool。

## W0b 历史知识核验

- 最近先例：`gtypist/2.10.1`（同 ncurses/6.6 平铺头 + HAVE_NCURSESW_*
  冲突 → compat-include/ncursesw/ 镜像层 + 前置 -I；env -u CONFIG_SHELL
  SHELL=/bin/sh + 绝对路径防 §12.38① getcwd 挂死）。
- `zzuf/0.15`（E114 umask 077→022 替换）、loksh/ivar（E074 -j1、R32/R39）。
- ncurses/6.6：单组件，libs=[formw,menuw,panelw,ncursesw]，pkg_config_name
  = ncursesw，头文件平铺 include/。

## 源码要点（tag tarball 5.8.16 实测）

- sha256 `3dcfb810cc6675cac6e3ea53775a6f819e0e12e0d2bde8122e3136b740f38ae5`
  （codeload 官方 tag 归档；release 无资产附件，此前 assets URL 404 已实测）。
- **自带预生成 configure**（autoconf 2.72 生成）；无 config.guess/config.sub
  （configure.ac 无 AC_CANONICAL_*）→ 不需要 --build 三元组。
- 构建体系：手写根 Makefile（非 automake）`-include config.make`；编译
  相对路径 `src/*.c`、对象落根目录 → in-source 构建。
- configure.ac:59-66：panel 探测命中 → COMPILE_MENU=1 + -DCOMPILE_MENU。
- `override CFLAGS += -O2`（环境 CFLAGS 仍生效）。
- install 目标经 tools/install.sh 装 bin/pspg（man-install 为独立目标，
  不随 install 执行）。
- 非 tty stdout + --csv/--tsv → 非交互渲染路径（pspg.c:2997）打印全部
  数据后 exit 0，不初始化 ncurses → 消费者测试的确定性验证入口。
- 版本串：src/pspg.h `PSPG_VERSION "5.8.16"`；`-V` 打印 `pspg-5.8.16`。

## 测试计划

- 上游：无可自动化测试套件（Makefile 无 test 目标；tests/test.sh 是
  100 轮循环 psql 输出流生成器，供人工观察）。按赛事规则说明原因
  （test_package/MANIFEST.yml），自补消费者测试。
- 消费者：test_pspg.sh 6 项断言：-V / --about / --help / 未知选项报错 /
  --csv 渲染 sample.csv / --tsv 渲染 sample.tsv，全部离线。

## 真机验证修正记录（2026-09-27，SHA 52adc533 首验中止后修正）

首验 configure 全过（E114/E074/R35/PostgreSQL NOTICE 均符合预期），
死于 make 首错：`src/pretty-csv.c:23: fatal error:
'ncursesw/curses.h' file not found`。根因：CPPFLAGS 只经命令行传给
configure，而 pspg 的手写根 Makefile（非 automake）不把 CPPFLAGS
落盘进 config.make；make 由 env -u CONFIG_SHELL 启动后拿不到该变量。
MateBook 诊断性重跑（残留构建目录 `make -j1 CPPFLAGS=...` 只读验证）
证明补上后全部 .o 编译 + 链接一次通过，`pspg -V` 输出 pspg-5.8.16。
修复：make 与 make install 命令行均显式重传
`CPPFLAGS="{self._cppflags}"`（install 目标依赖 all，须保持一致）。

## 留给 MateBook 的验证项

1. `conan download` ncurses/6.6、readline/8.3 确认二进制包可用（R35）。
2. conan create + conan test 完整跑通（configure → make -j1 → install →
   消费者测试）。
3. 关注点（失败时按下列顺序排查）：
   - configure 里 ncursesw 探测走 pkg-config 分支时需要 PKG_CONFIG_PATH
     指向 generators（AutotoolsDeps/conanbuild env 已含）；若设备无
     pkg-config 二进制，configure 走 -lncursesw 回退分支，compat-include
     平铺镜像已兜底，两条路径都应命中。
   - AC_CHECK_HEADERS(sys/inotify.h)：OHOS musl 若无 inotify 头仅降级
     watch 功能，属预期，不是失败。
   - AX_LIB_READLINE 会依次尝试 readline/edit/editline + termcap/curses
     组合；只要 readline/8.3 的 -L 生效，第一组合即命中。
   - 消费者断言 5/6 的渲染输出若为空：确认 stdout 重定向（非 tty）且
     fixtures 随 conan test 的 source_folder 可达（脚本经 $HERE 定位）。
4. `ohc-run.py finish pspg 5.8.16 built` → W4 审计（不跑 submit）。
---

**编译结束**: 2026-09-28 07:57
**最终状态**: built
