# zile 2.6.2 适配笔记（任务 #12377）

上游：`https://ftp.gnu.org/gnu/zile/zile-2.6.2.tar.gz`（2021-05-04 stable，1152751 B）。
范本：`archives/z/zile/2.6.4/`（同库已合入版，PR #10478）。本版本按其重建，
**但补丁不能照抄**——见问题 1/2。

## 上游测试口径（实跑在 `build()` 内）

| 来源 | 数量 | 取数 |
|---|---|---|
| `src/Makefile.am:104-106` `check_PROGRAMS = src/estr-test`、`TESTS = $(check_PROGRAMS)` | 1 | `grep -nE '^(TESTS\|check_PROGRAMS)' src/Makefile.am` |
| `tests/Makefile.am` `TESTS += $(LISP_TESTS) $(LISP_TESTS_ZILE_ONLY)` = 146 + 29 | 175 | 解析两变量块内的 `.el` 条目（探针 `tools/probes/z12377_testcount.cjs`） |
| **合计（automake 注册）** | **176** | |

磁盘上 `.el` 共 **177** 个：多出的 2 个是 `LISP_TESTS_ZILE_ONLY_FIXED_SCREEN`
（`scroll-up.el`/`scroll-down.el`），上游**只放进 EXTRA_DIST 与 `check-local`**
（需要固定 80x24 屏幕），不注册进 `TESTS` → 不是漏跑。声明 176 ≥ 实测 176。

## 问题表

| # | 症状 | 根因 | 处置 |
|---|---|---|---|
| 1 | `configure` 报 `cannot guess system type`（本版本自带 GNU config 2019-01-03 版 config.guess 不认 `uname -s=HarmonyOS`） | 2019 版分派块是 `echo ...; exit 0` 风格；2.6.4 的 2024 版是 `GUESS=` 变量风格 | 补丁 `0001` 在主 `case` 顶部加 HarmonyOS 分支，按机器名归一后 `echo "$GUESS_MACHINE-unknown-linux-ohos"; exit 0`。**与范本 0001 内容不同，按本版本 pristine tarball 重生成** |
| 2 | `config.sub` 把 `aarch64-unknown-linux-ohos` **静默改写**成 `aarch64-unknown-linux-gnu-ohos`（不报错，三元组失真） | 2019-01-05 版 config.sub 的「可接受基本系统类型」白名单没有 `linux-ohos*`，未命中就落到 `linux*)` 分支被 `sed s\|linux\|linux-gnu\|` 改写；GNU config 2021+ 才原生认 ohos（2.6.4 的 2024-05-27 版无需补丁） | 补丁 `0002` 白名单补一行 `linux-ohos*`。实测：打完 `sh build-aux/config.sub aarch64-unknown-linux-ohos` 原样回显 |
| 3 | `configure` 链接 `-lncursesw` 时 conftest 命令行只有 `-O3 -DNDEBUG`，**没有 -I/-L** → `ld.lld: error: unable to find library -lncursesw` → `configure: error: cannot find curses` | `AutotoolsToolchain.environment()` 会**当场**把 `extra_cflags`/`extra_ldflags` 拼进 CFLAGS/CPPFLAGS/LDFLAGS（`_resolve_*`）；范本 2.6.4 在 `env = tc.environment()` **之后**才 append → 追加被丢弃。2.6.4 侥幸没暴露，是因为它的 `AX_WITH_CURSES`（新版）走 **pkg-config**（`ncursesw.pc`）拿 CPPFLAGS/LIBS，而 `env.append_path("PKG_CONFIG_PATH", ...)` 是对已存在 EnvVars 的原地修改、不受快照影响；本版本 2.6.2 的 m4 是 2019 无 pkg-config 版，只能靠环境里的 `-L` | `generate()` 里把 `-I`/`-L` 的 append 移到 `tc.environment()` **之前**（`PKG_CONFIG_PATH`/`PATH`/`LD_LIBRARY_PATH` 仍在之后注入）。实测补丁后 `checking for Curses library... yes` |
| 4 | `configure` 的临时目录 `umask 077` + `mktemp -d ./confXXXXXX` 在 HMDFS 上 `Permission denied` | 全队已记录的 HMDFS 权限族问题（E011/E114 同族） | 补丁 `0003` 改 `umask 022`（两处，同范本 2.6.4 的 0002） |
| 5 | 设备无 valac，但 `src/*_vala.stamp` 规则无条件重跑 valac → `Error 127` | tarball 自带预生成 `.c`；`AM_PROG_VALAC(0.52)` 缺失只 WARN、Makefile 仍保留 `valac` | `make`/`make check`/`make install` 一律传 `VALAC=:`（POSIX no-op） |
| 6 | `doc/zile.1.in` 规则依赖新编译的 `src/zile` → 每次构建触发 help2man（设备无）→ `Error 127` | `AC_PATH_PROG([HELP2MAN],[help2man],[help2man])` | `ac_cv_path_HELP2MAN=/bin/true`（rc=0 不产出，保留 tarball 自带 man 页） |
| 7 | `make check` 的 175 个 lisp 用例全 `exit 1`，报 `Error opening terminal` | zile 是 curses 全屏程序，OHOS 无系统 terminfo 数据库 | `TERM=xterm` + `TERMINFO=<ncurses 包>/share/terminfo`（conan ncurses 包自带）；`tests/Makefile.am` 的 `TERM ?= vt100` 由环境变量覆盖 |
| 8 | gobject 运行期 `gtype.c:2556 static_quark_type_flags` 断言 SIGABRT | 制品仓 glib 只有 static 变体；libgee **shared** 内嵌另一份 static glib → 全图两份 gobject 类型系统 | `default_options = {"libgee/*:shared": False}` 使 glib 单实例（`--build=missing` 本地建 libgee static，glib/libffi/pcre2 仍取制品仓） |
| 9 | libtool 报 `'//lib/xxx.la' is not a valid libtool archive` | 制品仓包内 `.la` 记录了 conan relocatable 打包前的绝对路径 | `build()` 里删依赖 `lib/*.la`（libgee 配方同款） |

## 依赖

`glib/2.84.0`、`libgee/0.20.8`、`ncurses/6.5`（全部制品仓已发布，L0i/R36 干净）。
`libgee` 取 0.20.8 而非 0.20.8.1：后者只有配方无制品，CI 依赖解析必挂（同 2.6.4 口径）。

## 真机验证（`CONAN_HOME=~/work/psj/ch-zile12377`，conancenter 禁用、只留 ohpcd remote）

`CREATE_EXIT:0`；`make check` 汇总与消费者结论见设备日志
`~/work/psj/zile12377-ch1.log`（撞问题 3 那一轮）、`~/work/psj/zile12377-ch2.log`（通过轮）。
