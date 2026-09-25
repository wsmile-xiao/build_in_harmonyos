# mdocml 1.14.6 适配笔记

## 编译环境
- 构建系统: **手写 sh configure + Makefile**（非 autotools，不 autoreconf）
- 编译日期: 2026-09-24
- 编译器: clang（OHOS 适配版 conan 2.29.1 + `ci/conan/profiles/ohos-aarch64`）
- 状态: built
- worktree: `$HOME/ws/worktrees/mdocml-1.14.6` 分支 `feat/mdocml-1.14.6`
  （基线 `upstream/main` = `7f702efc1d070f666c0e1036cf79faaff7943ed6`）
- 许可: ISC（tarball `LICENSE` 原文 `Permission to use, copy, modify, and
  distribute this software for any purpose with or without fee…`）

## ⚠ 别名与同源披露（四项披露 a/b/c/d 的 a、b 落点）

**a) 问题表登记 + b) manifest/notes 同源关系**：

| 项 | 读数 |
|---|---|
| 别名事实 | tarball `INSTALL:5` 原文：`The mandoc manpage compiler toolset (formerly called "mdocml")` → **mdocml 是 mandoc 的旧名，同一上游软件** |
| 与 `archives/m/mandoc/1.14.6` 的关系 | **同一 URL、同一 tarball、同一 sha256**：`https://mandoc.bsd.lv/snapshots/mandoc-1.14.6.tar.gz` → `8bf0d570f01e70a6e124884088870cbed7537f36328d512909eb10cd53179d9c` |
| 两目录并存性质 | 属**任务卡包名（mdocml）与历史归档名（mandoc）的冗余**，非两个软件；本包 `mdocml/1.14.6` 是**同软件首个完整 Conan 配方**（旧 `mandoc/1.14.6` 仅 manifest/notes/2 补丁，**缺 conanfile.py/conandata.yml/test_package/commands.json**，2026-04-23 旧式归档） |
| 处置 | 不覆盖、不删改 `archives/m/mandoc/**`（属他人既有归档）；冗余形态提交维护方裁定归一或建别名映射（见 `feedback/pending/2026-09-24-mdocml-1.14.6.md`，**披露 c**） |

## W0 生死关

- **① 版本实核 = PASS**：官方 `mandoc.bsd.lv/snapshots` 与第二独立源
  MacPorts `distfiles.macports.org` 两次独立下载 sha256 **全等**
  `8bf0d570…d53179d9c`；tarball 内证：顶层目录 `mandoc-1.14.6`、
  `Makefile:18: VERSION = 1.14.6`。上游 git 两路（`github.com/Debian/mdocml`
  认证失败、`git.mandoc.bsd.lv` TLS eof）均不可达 → 按「官方可构建发行物」
  判据满足（官方渠道 2 源全等 + 版本内证）。Debian/Gentoo 镜像 404 不影响 ≥2 源。
- **② 硬依赖 = PASS**：`conan install . --build=missing -pr:h <绝对路径>/ohos-aarch64
  -pr:b <绝对路径>/ohos-aarch64` → **rc=0**（`zlib/1.3.1: Already installed!`）；
  `conan list -r=ohpcd zlib/*` rc=0 命中 7 版本。
- **③ 平台判据 = PASS（三项 rc=1 零命中）**：ISA 专属头
  （`altivec.h|<mmx>|3dnow|mmintrin|arm_neon|immintrin`）、glibc printf 钩子族
  （`printf.h|register_printf_`）、内联 asm（`__asm__( / asm(`）均零命中 →
  免编译探针定性、不触发 bcp 式收窄裁量、不触发止损。源码面 119 `.c` / 33 `.h`。
- **④ 缺硬依赖 = 空**（唯一硬依赖 zlib 在档且 rc=0 实证）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `sh ./configure` 全部 `tested *: no (compilation failed)`，并 `FATAL: no endian conversion functions found`、`FATAL: nanosleep: no` | 设备与 CI worker PATH **有 `clang` 无 `cc`**，上游默认 `CC="cc"` → `./configure: cc: inaccessible or not found`（`config.log` 逐条可见） | `configure.local` 给 `CC`/`AR` 取 profile 的 `tools.build:compiler_executables`（R33：整取 dict 再索引，**不读 shell 环境变量**，CI worker 上为空）→ configure rc=0 |
| 2 | `make` 报 `ln: cannot create hard link from 'mandoc' to 'man': Operation not permitted` → `Error 1` | HMDFS 不支持硬链接（`notes/device-facts.md` §一.21；旧归档 `mandoc/1.14.6/patches/0001` 同款） | `configure.local` 给 `LN="cp -f"`（上游 `configure.local.example:174` 官方手段）。**⚠ 值必须加双引号**：裸 `LN=cp -f` 被 shell 解析成「前缀赋值 + 执行 `-f`」→ configure **rc=127**（本任务实测踩过一次，`configure.local` 属 `. ./configure.local` 语义，赋值语句必须整体带引号） |
| 3 | `make regress` **1427 run / 19 failed**，19 项全部 `utf8:diff` | 设备**无 `locale` 命令**（`locale: inaccessible or not found`）→ configure `get_locale()` 里 `locale -a` 取不到 `en_US.UTF-8` → `HAVE_WCHAR=0`（`config.h: #define HAVE_WCHAR 0`）→ `-T utf8` 输出与 `.out_utf8` 期望不一致 | **一手实测定性**：`setlocale(LC_ALL,"")` 返回 `en_US.UTF-8`、`setlocale(LC_CTYPE,"en_US.UTF-8")` 成功、`wcwidth(L' ')=1`、`sizeof(wchar_t)=4`（`test-wchar.c` 调用序列逐条复现）→ `configure.local` 手工 `UTF8_LOCALE="en_US.UTF-8"` → `HAVE_WCHAR=1` → **19 失败清零，1427/1427 全绿**。属环境缺口非代码缺陷，**不记 NOT_RUN、不跳过** |
| 4 | 上游默认探测出 `STATIC="-static"` | configure `runtest noop STATIC -static` 在本机探测通过后选定 | `configure.local` 给 `STATIC=" "`（官方 `configure.local.example:279` 置空写法）规避静态链接面 |
| 5 | `make install` → `make: install: No such file or directory` / `Error 127` | 设备**无 `install` 命令**（`command -v install` 空，`/data/service/hnp/bin/install`、`/usr/bin/install` 均不存在）；且上游 `base-install` 内含硬链接与 `PREFIX` 绝对路径落盘 | **不走 `make install`**：`package()` 直接从源树收纳产物（可执行件 / `libmandoc.a` / 8 个对外头 / man1 页），man 别名按上游 `$(LN) mandoc <alias>` 语义手工复制 |
| 6 | zlib 头/库来源不稳 | 设备上 `zlib.h` 只在 **SDK sysroot**（`…/ohos/native/sysroot/usr/include/zlib.h`）与 harmonybrew（§一.4 假绿源）隐式可见，CI worker 不保证同路径 | 显式 `requires("zlib/1.3.1")` + 把 conan zlib 的 `include`/`lib` 注入 `CFLAGS`/`LDFLAGS`；conan `package_folder` 从 graph json 取真实 `p/` 目录（`conan cache path` 只给 export 目录 `e/`，§二.17 已知） |

## 上游测试（§3.5 两栏如实统计）

取数命令（均在解包源 `mandoc-1.14.6/` 下执行）：

```sh
# 输入栏
find regress -type f -name '*.in'   | wc -l   # → 572
find regress -type f -name '*.inc'  | wc -l   # → 6（被 .in 用 .so/include 引入）
# 期望输出栏
find regress -type f -name '*.out_*' | wc -l  # → 1189
find regress -type f -name '*.out_ascii'   | wc -l  # 565
find regress -type f -name '*.out_markdown'| wc -l  # 253
find regress -type f -name '*.out_lint'    | wc -l  # 249
find regress -type f -name '*.out_html'    | wc -l  # 68
find regress -type f -name '*.out_tag'     | wc -l  # 28
find regress -type f -name '*.out_utf8'    | wc -l  # 26
# 实跑（make regress → cd regress && ./regress.pl）
grep -E "tests run|NUMBER OF FAILED" regress.log
```

| 栏目 | 计数 |
|---|---|
| **输入 `.in`** | **572**（与任务卡「572 输入」完全吻合） |
| **期望输出 `.out_*` 合计** | **1189** = ascii 565 + markdown 253 + lint 249 + html 68 + tag 28 + utf8 26 |
| **实跑 tests run** | **1427**，**failed 0**（约 89 秒） |
| 分项实跑 | ascii **565** + tag **28** + man **244**、utf8 **21**、html **68**、markdown **253**、lint **248** |

四分项：`TOTAL=PASS+FAIL+SKIP+NOT_RUN` → **1427 = 1427 + 0 + 0 + 0**。

**期望文件数 vs 实跑数的三处差额逐项归因（rule4 防线）**：

| 差额 | 期望 | 实跑 | 归因（已定位到具体文件） |
|---|---|---|---|
| lint | 249 | 248 | **差 1 = `mdoc/Xr/args`**：其 `mdoc/Xr/Makefile:5` 是 `# OpenBSD only: .Xr target tests cause too much trouble elsewhere`，`LINT_TARGETS = args` 位于该行**之后**；上游 `regress.pl` 的 `parse_makefile` 有 `last if /^# OpenBSD only/` → 提前终止解析、**上游有意不注册**。期望文件 `mdoc/Xr/args.out_lint`(462B) 与输入 `args.in`(526B) 均存在。**证据**：按 perl 解析口径模拟出的注册集 = 248（`lint_reg_perl.txt`），与实跑产物 `*.mandoc_lint` 集合（`lint_ran.txt`，248）comm 双向差集**恰好只有这一项** |
| utf8 | 26 | 21 | **差 5 = `char/unicode` 的未注册项**：`char/unicode/Makefile:9` `UTF8_TARGETS = ascii invalid man mdoc namediff` 只注册 5 项，`.out_utf8` 却有 10 个（ascii/input/invalid/latin1/latin1diff/man/mdoc/named/namediff/nogroff）→ 未注册的 input/latin1/latin1diff/named/nogroff 5 项属上游注册面收窄 |
| ascii/tag/html/markdown | 565/28/68/253 | 565/28/68/253 | 无差额 |
| man | —（无独立期望文件） | 244 | `regress.pl` 的 `man:` 段做的是**二次回读比对**：`-T man` 产出 `.in_man` → 再用 mandoc 以 `-man -T ascii` 回读 `.mandoc_man` → 与 `.out_ascii` 比对，不新增期望文件 |

**关于任务卡「≈1468 期望输出」**（编排方裁决：以实测两栏为准，不为对齐任务卡凑数）：
- 我实测期望输出文件 = **1189**，**低于**任务卡约数 1468（差 279）；
- **方向安全**：rule4 红线是「实测 > 声明」（少报），本例 声明(1468) > 实测(1189)，不存在少报风险；
- 任务卡「≈1468」按约数提示对待，**非判据**；判据 = 实测两栏 + 上列取数命令（审方可独立复算）；
- **1468 与 1427（tests run）/ 1189（期望文件）均无对应物理集合**：`regress/` 总文件 1908 = `.in` 572 + `.out_*` 1189 + `.inc` 6 + 各层 `Makefile` 139 + `regress.pl` 1 + `regress.pl.1` 1 + 杂项 8；**「差额 41（1468−1427）无对应集合」这一句如实保留**，我不为它硬凑解释。

## 依赖版本
- **zlib/1.3.1**（制品仓在架；`conan list -r=ohpcd zlib/*` 命中 1.3.1 / 1.3.1.1 /
  1.3.1.1.1 / 1.3.1.1.1.1 / 1.3.1.1.1.1.1 / 1.3.1.2 / 1.3.2 共 7 版本）。
  链接期 `-lz` 由 configure 硬编码进 `LDADD`，路径由 `LDFLAGS=-L<conan>/lib` 指向
  conan 包（**静态 `libz.a`**，满足 R26 系统同名库静态隔离）。
- 测试期 **perl 5.42.0**（HNP `/data/service/hnp/bin/perl`，symlink →
  `perl.org/perl_5.42.0/bin/perl`；`perl -e 'print $]'` → `5.042000`）。
  **不作 conan `tool_requires`**（conan perl 有 HMFS 不可用先例）。
- `diff` = **GNU diffutils 3.10**（`/data/service/hnp/bin/diff`），
  `regress.pl` 的 `diff -au` 回退链不触发 toybox 格式差异（§一.24 不适用）。

## 交付物形态
- `bin/`：`mandoc`（主程序）、`man`、`apropos`、`whatis`、`makewhatis`
  （四者 = `mandoc` 副本，上游 `$(LN) mandoc <alias>` 语义，LN=cp -f 后为独立文件）、
  `demandoc`、`soelim`
- `lib/libmandoc.a`（静态，上游唯一库产物，**无 `.so`** → R26/G3 天然满足）
- `include/`：`eqn.h` `man.h` `mandoc.h` `mandoc_aux.h` `mandoc_parse.h`
  `mdoc.h` `roff.h` `tbl.h`（= 上游 `lib-install` 安装清单）
- `share/man/man1/`：`mandoc.1` `demandoc.1` `soelim.1` `man.1` `apropos.1`
- `licenses/LICENSE`
- 软件级 `commands.json`（R38/PF8：`bindirs` 非空 → CLI 包必备）

## 源码修改
**无源码补丁**（`patches_applied: []`，不创建 `patches/` 目录）。
全部平台差异经上游官方注入位 `configure.local` 承载，属标准配方适配、
**无需 `refresh_patch` 两面登记**（对齐 symphony DRAFT-E678 口径：
build() 内同名函数/官方注入位修法 = 标准配方适配，免 refresh_patch 登记）。
未修改上游任何测试、构建或源文件。
