# combine

`combine` 是 GNU 的"对文本文件的**行**做集合运算"的命令行工具：它把一个**数据文件**
的每条记录按选定字段（默认空白分隔，可用 `-D` 指定分隔符）作键，去查一个或多个
**引用文件**的哈希表，再按 `-o` 的字段清单产出结果。除了并/交/差/补这类直观运算，
它还能做连接（join）、唯一化（`-u`）、计数（`-n`）、字段求和（`-s`）、常量注入
（`-K`）、以及用 guile 脚本改写字段（`-x`/`-X`，可选）。

上游 [GNU combine](https://www.gnu.org/software/combine/)（作者 Daniel P. Valentine，
GPL-2.0-or-later，最后发布 0.4.0 / 2013）。

## 功能概述

- `combine` — 唯一的可执行程序（`src/Makefile.am` 的 `bin_PROGRAMS = combine`）。
  常用选项：`-o` 输出字段清单、`-w` 写出、`-t` 指定输出文件、`-D`/`-d` 输入/输出
  分隔符、`-r` 引用文件、`-k`/`-m` 键字段、`-u` 唯一化、`-n` 计数、`-s` 求和、
  `-z` 计数宽度、`-K` 常量、`--statistics` 把记录计数写到 stderr。
- `lib/libdf.a` 是 `noinst_LIBRARIES`（自带 getopt/version-etc/extras 的私有支撑库），
  **不安装、不进包**；本包没有 `.a`/`.so` 产物。
- `src/util.scm` 与 `src/combine_scm/{calendar,parse}.scm` 是 guile 扩展载荷，
  装到 `share/combine_scm/`（见下方 OHOS 适配要点 5）。

## 依赖关系

- 编译依赖：无 Conan 依赖。构建工具由 CI worker 环境提供（`make`、`clang`、`perl`、`/bin/sh`）。
  **不需要** `autoconf`/`automake`（tarball 已带生成好的 `configure` 与 `Makefile.in`）、
  `msgfmt`/`autopoint`（`--disable-nls`）、`makeinfo`、`yacc`/`bison`（`AC_PROG_YACC`
  只是探测，`src/` 里没有 `.y` 文件）。
- 可选依赖：**guile** —— `configure.ac:26` 用 `AC_CHECK_LIB([guile],[gh_scm2bool])`
  探测，但没有任何 required/`AC_MSG_ERROR` 判定，且全部 guile 代码都在
  `HAVE_LIBGUILE`/`HAVE_LIBGUILE_H` 条件编译之内（`src/df_common.h`、`src/main.c`，
  唯一 guile 翻译单元是 `src/iguile.c`）。⇒ HarmonyOS 侧不部署 guile 也能正常构建。
- 运行依赖：无第三方库（纯 C，链接 musl）。

## OHOS 适配要点

1. **autotools 快照极旧**：`config.guess`/`config.sub` 都是 `2004-03-12`。
   `configure` 会跑 `$SHELL config.guess`（configure:6960）⇒ 不识别 `uname -s` =
   HarmonyOS 时直接 `cannot guess build type`（E160/E007 族）。补丁
   `0001-config.guess.patch` + `0002-config.sub.patch` 按**本快照自己的风格**
   （per-branch `echo <triplet>; exit 0 ;;`，`grep -c 'GUESS=' config.guess` = 0）生成。
2. **不用 `--build/--host` 绕**：那会把原生构建伪装成交叉编译，
   `AC_FUNC_MALLOC`/`AC_FUNC_MMAP`/`AC_FUNC_MBRTOWC`/`AM_C_PROTOTYPES` 这类
   `AC_RUN_IFELSE` 探测会静默走 cross 分支。
3. **HMDFS/环境两处坑**：profile 注入的 `CONFIG_SHELL=hnp bash` 在构建目录里
   `getcwd()` 必挂（⇒ 全部构建命令加 `env -u CONFIG_SHELL SHELL=/bin/sh`）；
   autoconf 写进 `config.status` 的 `umask 077 && mktemp -d` 在 HMDFS 上建出
   不可写的目录（⇒ 补丁 0003 改成 `umask 002`，同目录 A/B 实测）。
4. **上游有自动化测试且必须真跑**：`tests/Makefile.am` 用手写 `check:` 目标调
   `tests/test_combine`，内含 **7 个用例**、**15 次 `diff -q` 黄金比对**。配方 `build()`
   里执行 `make -j1 check`，实测 **6 通过 / 1 失败**：失败的是 Test 7
   （`-X ../src/util.scm`，guile 扩展用例）⇒ 分母保持 7，不删用例、不改标 skipped。
   另注意上游脚本自身退出码恒为 0（末条命令是 `rm`），所以判决必须逐用例点收日志。
5. **关 guile 的两处后果**：`-x`/`-X` 与三个 `.scm` 载荷在实际二进制里不可用；
   以及 `@GUILE_SITE@` 为空会把 `src/combine_scm` 的安装目录退化成 `/combine_scm`
   ⇒ 配方用 make 命令行变量把它覆盖到 `share/combine_scm`。
6. **NLS 关闭**：`--disable-nls`（目标上没有 libintl 运行时，也没有 locale 数据面），
   `po/` 的消息目录不安装，界面语言只有英文。

## 参考资料

- 项目主页与下载：<https://www.gnu.org/software/combine/>
- 源码归档：<https://ftp.gnu.org/gnu/combine/combine-0.4.0.tar.gz>
  （sha256 `56e71cd9cc38404fc4e6dac02d5fb76e894d481f9be8719072b1f8b1d8afbe14`）
- 完整选项语义：`combine --help`，或上游 info 手册 `info combine`
- 适配细节、失败方案与测试台账：<https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos>
  本目录 `0.4.0/notes.md`
