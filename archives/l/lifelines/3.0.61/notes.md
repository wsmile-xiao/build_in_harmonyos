# lifelines 3.0.61 适配笔记（任务 #8463）

## 上游坐标

- 项目：LifeLines 家谱系统（文本/curses 前端 `llines` + 批处理报告执行器 `llexec`），
  Homebrew formula `lifelines`（"Text-based genealogy software"，license MIT）。
- 上游仓库：https://github.com/lifelines/lifelines ，任务版本 3.0.61 对应 **tag `3.0.61`**。
- 取源码：tag 归档（codeload 与 github archive 两条 URL 字节一致）
  `sha256 = 9eb469bca4123f1edd7e23162175bb426fa2f954aee8f113fa938957bc585e73`，
  2026-10-03 在本机与真机分别下载对拍一致。
- 官方 **release** 资产只到 3.1.1（`releases/download/3.0.61/lifelines-3.0.61.tar.gz` 回 404），
  3.0.61 只能取 tag 归档 ⇒ 归档里没有生成的 `configure`（git export），必须自带 autotools 引导。

## 构建系统

autotools（`configure.ac` + 19 个 `Makefile.am`，2007 年的 gettext/aclocal 宏目录
`build/autotools`）。产物是可执行程序（`package_type = "application"`），
因此按 L0k/R38 在软件级目录提供 `archives/l/lifelines/commands.json`。

## 引导链（build() 里真实执行）

`aclocal → autoheader → automake --add-missing --copy --foreign → autoconf → configure → make`

tool_requires 全部走制品仓二进制：`perl/5.42.2`、`autoconf/2.72`、`automake/1.18`、
`libtool/2.5.4`、`m4/1.4.19`、`bison/2.7`；运行期依赖只有 `ncurses/6.6`。

- **bison 必须留在 2.x**：`src/interp/yacc.y` 用旧式 `%pure_parser` + `yyparse(void *)`，
  bison 3.8 生成的是 `int yyparse (void)`，与 `src/interp/parse.h` 的声明冲突。
  制品仓同时有 `bison/2.7` 与 `bison/3.8.2`，取 2.7。
- 归档里签入了 `src/interp/yacc.c`，但 **没有** 签入 `yacc.h`（`EXTRA_DIST = yacc.h` 只出现在
  `make dist` 产物里）。automake 的规则是
  `yacc.h: yacc.c` →「若 yacc.h 不存在就 `rm -f yacc.c` 再 `make yacc.c`」；
  而 srcdir 那份 `yacc.c` 让第二步直接回答 "is up to date"，头文件永远不生成，
  `lex.c` 卡在 `#include "yacc.h"`。配方在 build() 里删掉这份签入的生成物，
  由 bison 2.7 从 pristine `yacc.y` 重新生成 `yacc.c` + `yacc.h`。

## 鸿蒙 PC 上的四个真机坑（都是实测，不是猜）

1. **设备 profile 把 PATH 换成了一份不含 `/usr/bin` 的清单**。toybox 的
   `dirname`/`printenv`/`sed`/`expr` 全在 `/usr/bin` 下（symlink 到 `/bin/toybox`），
   于是 conan 生成的 env 脚本里 `printenv` 静默失败、autoconf 的 `bin/autom4te` 包装脚本
   `dirname: inaccessible or not found`、`configure` 走到 config.guess 后
   `sed: command not found`。配方因此不依赖 conan 的 PATH 拼接，
   每次 `self.run` 自带 `PATH="<制品仓工具 bin>…:<环境 PATH>:/usr/bin"` 前缀。
2. **perl 一致性**：制品仓 `autoconf/2.72`、`automake/1.18` 是 perl 脚本，其 buildenv 只导出
   `PERL5LIB`（指向 perl 5.42.2），而 PATH 里排在前面的是 harmonybrew 的 perl 5.44，
   结果宿主 perl 去加载 5.42.2 的 XS 模块：
   `Cwd.so: Perl_newSVsv_flags: symbol not found`。修法同样是把制品仓 perl 的 bin 放到
   PATH 最前，并显式给出该 perl 的 `@INC`（制品仓 perl 被重定位过，
   编译期烧进去的 `//lib/perl5/5.42.2` 不存在，不给 PERL5LIB 会 `Can't locate strict.pm`）。
3. **制品仓 automake 的包装脚本 shebang 写死 `/data/service/hnp/bin/perl`**：
   `bin/aclocal`、`bin/automake` 是 `/bin/sh` 包装，exec 同目录的 `.aclocal-real`/`.automake-real`，
   后者的 shebang 指向 CI worker 才有的 `/data/service/hnp/bin/perl`；真机没有这个路径，
   报的却是 "`No such file or directory`"（文件明明在，是解释器不存在）。
   配方直接 `perl <pkg>/bin/.aclocal-real --automake-acdir=… --system-acdir=…`
   （以及 `--libdir=…`），参数与包装脚本一致，CI 与真机同一条路径可用。
4. **HMDFS 上 `umask 077` + `mktemp -d` 建出来的目录自己写不进去**（E114/E129），
   `config.status` 无法在自己的临时目录写 `subs1.awk`；配方只放宽**生成出来的** configure
   里这两行（`(umask 077 && mktemp -d …)` → `mktemp -d …`），不动上游源码。

## 补丁（5 个，全部按 pristine tag 归档逐字节生成）

| 补丁 | 类型 | 内容 |
|---|---|---|
| `0001-src-stdlib-environ.c.patch` | portability | `environ_determine_tempfile()` 先认 `TMPDIR` 再退回 `/tmp`（真机 `/tmp` 只读） |
| `0002-configure.ac.patch` | portability | 摘掉 2007 年的 `AM_GNU_GETTEXT`/`AM_ICONV` 块与 `intl`/`po` 输出项，`@LIBINTL@`/`@LIBICONV@` 置空（本移植关闭 NLS） |
| `0003-Makefile.am.patch` | portability | `SUBDIRS` 去掉 `intl`/`po`；`ACLOCAL_AMFLAGS` 补 `-I m4` |
| `0004-reports-st-Makefile.am.patch` | platform | selftest 调 `llexec` 时把 `-x <脚本>` 放在 `<库>` 之前（本 libc 的 `getopt()` 不置换 argv，原顺序直接不吃选项） |
| `0005-build-autotools-config.sub.patch` | portability | 2007 版 `config.sub` 认识 `linux-ohos` 这一 KERNEL-OS 组合，`--host=aarch64-unknown-linux-ohos` 才能规范化 |

## 上游测试套件（真机实跑）

`reports/st/Makefile.am` 注册 `TESTS = selftest`（harness 层 1 个脚本），
`selftest = ti + test_iter + st_all`，内部做 **8 次 golden-file 比对**
（test_iter 6 次 + st_all 2 次）。取数命令：`ls reports/st/*.ref | wc -l` = 8。

配方 `build()` 里在 `make` 之后真实执行
`TMPDIR=<build>/tmptest TERM=xterm make -k check`（cwd `<build>/reports/st`），
再把 8 份产物逐份与上游随包的 pristine `.ref` 全文比对，逐项打印 PASS/DIFF，
结果落 `reports-st-results.txt`。真机结果见 PR 正文（`07:xx` 那一轮 create 日志）。

三条比对不达标的技术原因（逐条对拍取证，非平台借口）：

1. `st_all.out` 与 `st_all.ref` 都是 310 行，差异只有 1 块的第一行：我们 `version: 3.0.61`、
   参考件 `version: 3.0.49`——上游是从 3.0.49 生成的参考件，任何非 3.0.49 的二进制都不可能
   逐字节复现它（其余 309 行含全部人名/日期/表格输出，逐字相同）。
2. `st_all.stdout` 是一次交互式会话的整段转写，比对差异 2 块（我们 77 行 vs 参考件 40 行），
   内容全部指向同一个原因——**本机没有 codeset/locale 支持**：本移植按 0002/0003 关闭 NLS 与
   `AM_ICONV`（上游 2007 年的 gettext 树要 `po/`、`intl/` 的发行件，tag 归档里没有，留着
   `configure` 连 `Makefile` 都生不出来）。于是我们这一侧多出
   `Locale missing: en_US (English) / it_IT (Italian) / sv_SE (Swedish)`、
   成批 `convertcode(...,UTF-8,ISO-8859-*) ... FAILURE`，并且小计行与参考件不同：
   `Passed 4/36 convert tests`（参考件 28/36）、`Passed 0/22 string UTF-8 tests`（参考件 20/22）、
   `Passed 581/584 (skipped 12) date tests`（参考件 598/598）。
   这些差异与 3.0.61/3.0.49 无关，是 charset/locale 能力面不同，任何关掉 iconv 的构建同样对不上。
3. `trigtest.ref` 期望 `House Lon: -80 degrees, …`，实际输出 `4294967216 degrees, …`
   （同一行十进制部分 `-80.51 degrees` 是对的）。`4294967216 = (unsigned) -80`：
   报告语言里 `d()` 内建在 LP64 下把负的经纬度分量按无符号渲染，
   属上游既有 64 位缺陷，在任何 64 位 Linux 上同样复现，不是本移植改出来的行为。

## 适配后（鸿蒙特有）测试

`test_package/check_lifelines.py` 从**已安装**的包出发（PATH 与 TERMINFO_DIRS 由 conanrun
提供，`TERM=xterm`）跑 23 条断言：`llines`/`llexec` 可解析、两者 `--version` 横幅含 3.0.61、
按上游 selftest 的同一按键序列（`yurti` + `yyq`）从上游 `ti.ged` 建出数据库并校验库目录的
`aa`、`ab` 两个子目录与 `key`、`xrefs` 两个文件、两个消费者自写报告程序
（个体遍历 + 家庭/配偶导航）逐条核对输出内容（`1: I1`…`10: I12`、`1: F1`、
`    1: I2`、`    2: I3`）、以及三条负向路径：报告文件不存在必须报
`Program contains errors.`、被解释器拒绝的程序必须报 `Syntax Error`（两者都不得出现成功标记）、
库不存在必须落到 `There is no LifeLines database` 提示而不是假成功。
每条命令都带超时且 stdin 缺省接 `/dev/null`（上游 llexec 在缺库时会退回交互模式，
不给边界就会挂住整个套件）。

## 与图谱/知识库的关系

路径 A。踩到的坑（PATH 缺 toybox、制品仓 perl 一致性、包装脚本 shebang、HMDFS umask）
都属"这一台机器/这一份 profile 的环境事实"，不是可复用的一类机制，
且 `st_all.ref` 版本烙印是上游自身问题，故不另立知识草稿。
