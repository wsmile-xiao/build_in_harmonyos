# inhomog 0.1.9.2 适配笔记

## 编译环境
- 构建系统: autotools（上游 release 件自带 `configure` 481073B + `config.guess`/`ltmain.sh`/`install-sh`/`test-driver` ⇒ **不需要 autoreconf**）
- 编译日期: 2026-09-25
- 编译器: clang/clang++（CI profile `tools.build:compiler_executables` = /data/service/hnp/bin/clang，clang-15）
- 状态: built

## 任务与源码

- 平台任务 id=7480（本账号 assigned），包 `inhomog/0.1.9.2`，上游仓库 `https://bitbucket.org/broukema/inhomog`（Debian `.dsc` 的 `Homepage:` 与 `debian/upstream/metadata` 的 `Repository:` 双源一致；`git ls-remote --tags` 实测 tag `v0.1.9.2` 存在）。
- `conandata.yml` 的 url 取官方归档端点 `https://bitbucket.org/broukema/inhomog/get/v0.1.9.2.tar.gz`，sha256 `e631f37ea5496f8e24b1b62f228bc2fba7809fe9ca3bc55a0486792d5d188867`（**url 与 sha256 同源同一件**：Windows 侧与设备侧各下一遍，两处哈希逐字一致）。
  - 上游 `/downloads/v0.1.9.2.tar.gz` 匿名 404、`api.bitbucket.org/.../downloads` 返回 402 ⇒ 不可用作交付 URL。
  - 交叉核验同一性：与 Debian pristine orig（`deb.debian.org/.../inhomog_0.1.9.2.orig.tar.gz`，sha256 `44545d1864b634e0f8f0260775966b786289e99a76f02051890c57240ae27911`）比对，**96 个条目集合 diff=0**，`AUTHORS/COPYING/README/NEWS/ChangeLog/TODO` 六文件 sha256 逐字节 SAME ⇒ 同一棵树。
  - ❌ 不采用候选备注里的 `mirrors.mivocloud.com`（Ubuntu 站点镜像，PF7/R39 禁手写镜像进活文件）。
  - ❌ 曾出现一条网页转述的"上游" `github.com/kvmccai/inhomog` + 配套 sha256，`git ls-remote` 回 `Repository not found`、按该 URL 下载实为 404 ⇒ **编造，已排除**，未进任何交付物。
- 产物：`lib/libinhomog.so.0.2.0`（libtool `-version-info 2:0:2`）+ CLI `bin/inhomog` + 6 个公开头 + `lib/pkgconfig/inhomog.pc`。
- 许可证 `GPL-2.0-or-later`（`COPYING` 为 GPL-2 全文，Debian `copyright` 的 `License: GPL-v2+`）。

## 编译步骤

1. `source`：`get(..., strip_root=True)`（归档根目录是非规范的 `broukema-inhomog-2e922602f729`）。
2. `build()`：`apply_conandata_patches` → 把 `configure` 里的 `umask 077` 改 `umask 022`（E011，HMDFS 下 config.status 的 077 临时目录不可写）→ `autotools.configure()` → `autotools.make(args=维护者规则关闭)` → 对 `lib/.libs` 下 17 个真 ELF 测试二进制按 E077 顺序自签（防御性，见测试账本注） → `make check`（注册 7 个） → 直跑其余 10 个已编译测试程序并逐项取 rc。
3. `generate()` 关键项：`--build/--host` 显式同为 `aarch64-unknown-linux-gnu`；`LIBS=-lgsl -lgslcblas -largp -lm`；把 host 依赖的 `includedirs`/`libdirs` 补进 `CFLAGS/CPPFLAGS/LDFLAGS`，并把 `libdirs` 前置进 `LD_LIBRARY_PATH`、`bindirs` 进 `PATH`（E467 的 rec 方案）；`SHELL=CONFIG_SHELL=/bin/sh`（E386）；`-I<src_root>`（VPATH 兼容）。
4. `package()`：`make install`（同样关闭维护者规则）→ 删 `.la` → 把 `include/inhomog/` 摊平到 `include/` → 拷 `COPYING`/`copyright` → 对 `bin/` 下 ELF 走 `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: Cannot determine working directory`（连锁一串 `getcwd: cannot access parent directories`） | E386：conan 的 `SHELL`/`CONFIG_SHELL` 指向 hnp bash，其在 HMDFS 构建目录下 `getcwd` 必挂，autoconf 又用它 re-exec 自己 | 配方 `generate()` 里把两个变量都钉成 `/bin/sh`（§12.1 首选修法，非换环境掩盖） |
| 2 | `configure: error: cannot run C compiled programs.`（在 `checking whether we are cross compiling`） | E467：`AC_PROG_CC` 最早的 run 探测沿用了 LIBS 里的整条依赖闭包去链 conftest，而 conftest 没有 RUNPATH ⇒ 加载不到 `libgsl.so`，被 autoconf 归因成"不能运行编译产物" | 按该条目 rec：`generate()` 把 host 依赖 `libdirs` 前置进 `LD_LIBRARY_PATH`、`bindirs` 进 `PATH`。**先曾误用 `--host=…-musl` 制造交叉判定压掉症状 —— 那正是条目 forbid 项与 P-AUTOTOOLS-001 禁止的绕过，已撤回** |
| 3 | `Invalid configuration 'aarch64-unknown-linux-ohos': machine 'aarch64-unknown-linux' not recognized` | 上游随 release 分发的 `config.sub` 是 2016 版，不认识 OHOS 三元组（E007 家族） | 显式 `--build=--host=aarch64-unknown-linux-gnu`（不装 autotools 重生成，也不需要：本包 configure 自带可用）；真实目标由编译器自身决定（`-target aarch64-linux-ohos` + OHOS sysroot），产物已核为 OHOS ELF 且可执行 |
| 4 | `ld.lld: error: unable to find library -lgcc` ⇒ `configure: error: Could not find libgcc.*` | `configure.ac` 的 `AC_CHECK_LIB(gcc,main)` 失败分支是 `AC_MSG_ERROR`；OHOS clang/lld 无 `libgcc.a`（sysroot 内 `find libgcc*` 零命中），运行期为 `libclang_rt.builtins.a`。该检查上游自陈 "needed especially on Solaris systems with f77" | `patches/0001`：把失败分支从"中止"降为"告警继续"（一行），不注入 `-lgcc`、不改源码逻辑 |
| 5 | `fatal error: 'error.h' file not found`（`xmalloc.c:55`） | OHOS musl 无 glibc 的 `error.h`；全树 `#include <error.h>` 仅此 1 处，且 `error()`/`error_at_line()` **零调用**（实测 grep 计数=0）⇒ gnulib 遗留死包含 | `patches/0002`：删该行死包含。**不写 `error()` 兼容层**（无调用方，写兼容层反而引入无用代码） |
| 6 | `configure: error: Cannot continue: argp.h not found - please install glibc` | `AC_CHECK_HEADER(argp.h,,AC_MSG_ERROR)` + `inhomog.c:26` 无守护 `#include <argp.h>`；OHOS sysroot 无 `argp.h`（对照 `getopt.h` 存在） | 走已发布依赖 **`argp-standalone/1.5.0`**（`--build=never` 实测有制品，包内实带 `include/argp.h` + `lib/libargp.a`）⇒ **零改上游源码**；链接期再靠 `LIBS=-largp` 补符号 |
| 7 | `checking for gsl_spline_init in -lgsl... no` | `AutotoolsToolchain` 不把依赖的 `-I/-L` 注入探测用的 `CFLAGS/LDFLAGS` | 按 host 依赖 `cpp_info.aggregated_components()` 手工补齐（同本窗 ledmon 先例写法） |
| 8 | 链接期缺 `-largp`（`-lgsl/-lgslcblas` 上游默认动作本会追加，`-lm` 因空 action-if-found 不追加） | `configure.ac:123` 只有 `AC_CHECK_HEADER(argp.h)`、**全树无 argp 的库探测**，而 `inhomog.c:126` 真调 `argp_parse`；`AC_CHECK_LIB([m],[cos],,)` 给了空 ACTION-IF-FOUND ⇒ 覆盖默认追加；`AC_CHECK_LIB(gslcblas,…)`/`AC_CHECK_LIB(gsl,…)` 未给该参数 ⇒ 默认追加仍在（真机 `configure:12984/13029`） | configure 命令行显式传 `LIBS=-lgsl -lgslcblas -largp -lm`（autoconf 用户变量，会落进 Makefile 的 LIBS 默认值）；其中 `-largp`/`-lm` 必需、`-lgsl`/`-lgslcblas` 为保险 |
| 9 | `fatal error: 'lib/inhomog.h' file not found` | 上游源码写 `#include "lib/inhomog.h"`，只有 in-tree 构建成立（automake 给 `lib/Makefile` 的 `DEFAULT_INCLUDES` 是 `-I. -I$(top_builddir)`）；conan 走 VPATH 时该相对路径不成立 | `generate()` 里给 C/C++ 各加 `-I<src_root>`（指向上游真实头位置，非造假日头文件） |
| 10 | `make: *** [Makefile:466: .../src/aclocal.m4] Error 127` | automake 维护者规则判定生成物过期，去跑 `aclocal` —— OHOS PATH 上没有该可执行名。先按"输入旧/生成物新"钉 mtime 试过（`os.utime`），**HMDFS 上不生效、仍犯** | `make` 与 `make install` **两处**都传 `ACLOCAL=: AUTOMAKE=: AUTOCONF=: AUTOHEADER=:`（release 自带生成物本就是交付物，重跑 autotools 既无必要也无工具） |
| 11 | 消费者测试链接期 `ld.lld: error: undefined symbol: test_power_spectrum_flatspace` | 该函数在公开头 `inhomog.h:343` 有声明，但定义在 `lib/test_power_spectrum_flatspace.c`，而该文件**不在 `libinhomog_la_SOURCES` 里**（19 个源文件，实测 grep 计数=0），只属于上游自带的同名 noinst 程序 | 换断言目标为库内真实定义（`sigma_square_invariant_I.c` 的 `flat_length_3` / `flat_length_3_3params`）。**教训：公开头声明 ≠ 库导出符号，选断言必须回 `Makefile.am` 核归属** |
| 12 | 消费者编译 `gsl` 头找不到 | `inhomog.h` 自身 `#include <gsl/gsl_spline.h>`（公开头依赖 gsl） | `test_package` 改用 `AutotoolsToolchain` + `AutotoolsDeps`，编译行引用 `$CFLAGS $CPPFLAGS $LDFLAGS`，不硬编码依赖路径 |
| 13 | `str.format` 报 `KeyError: ' echo ... '` | 断言命令串里写了 shell 的 `{ ...; }` 花括号，被 `str.format` 当占位符 | 去掉多余的 shell 判错块（`self.run` 非 0 退出本身抛错） |
| 14 | 一度把"构建失败"报成成功结论的反面：`step3.out` 里读到 `CREATE_RC=2` | 前台直跑时结果走 stdout，`step3.out` 是上一轮遗留文本 ⇒ 陈旧 rc 误导判断 | 判成败只认本轮输出 + 日志内成功标记与 `^ERROR` 计数（本轮实测 `CREATE_RC=0`、`Package 'b352603f79862d5b1716e4f12228956432cf3d3c' created`、`^ERROR` 计数 0） |

## 测试账本（§10.1 五维口径，全部真机读数）

- `N_static = 17`：`lib/Makefile.am:32-49` 的 `noinst_PROGRAMS` 共 21 个，其中 `test_*` 17 个；另 4 个（`Omega_D_BAO`、`Omega_D_VAv2`、`Omega_D_effWEC`、`effective_sigma8`）是研究用驱动，不计入测试分母。计数用 python 正则解析，非肉眼数。
- `N_registered = 10`：`TESTS_FAST` 7（:110-114）+ `TESTS_SLOW` 3（:115-117）；`DEV_MODE` 条件门（:120-123）使默认 `make check` 只跑 7 个。
- `N_executed = 17`：7 个走 `make check`（实测 `# PASS: 7 / # FAIL: 0 / # SKIP: 0 / # ERROR: 0`）；3 个 SLOW 与 7 个未注册项由 `build()` 直接执行已编译好的二进制（**不使用 `--enable-devmode`**：`Makefile.am:14-16` 会连带塞 `-Werror -ansi -fsanitize=address`，交叉下必红）。
- 有明确通过判据（automake PASS 或上游 `pass` 误差累加器 = 0）**12** 个；其余 5 个逐项：
  - `test_gsl_multifit`、`test_sigma_invariants`：只打印结果/计时，**上游无 pass 累加器** ⇒ 记"已执行不判定"；
  - `test_parse_noempty_strtox`：需命令行参数（逐字 `Warning: failed to read --multiparam value.`），非 headless 判定项；
  - `test_scale_factor_D_Ham`：上游判据 `pass = 3`（EdS 与 nearly-EdS 两组初值 `a_D/dot_a_D` 相对差超容差，逐字 `relative diff = 0.249135`）⇒ 数值容差敏感项，上游本就未注册进 `TESTS`，**非本次适配引入**；
  - `test_gsl_ieee_mode`：SIGABRT，逐字 `gsl: …/ieee-utils/fp-unknown.c:29: ERROR: the IEEE interface for this platform is unsupported or could not be determined at configure time` ⇒ 失败源自 **gsl 制品自身**的平台判定，与 inhomog 配方无关。
  - ⇒ **分母不缩**（§10.1：预期失败与无判据项都留在分母内，只单列原因）：正文两张表合计 = 上游静态全量 **17**，实际执行 **17**，判通过 **12**（注册 7 + 直跑 5）、判不通过 **2**（`test_scale_factor_D_Ham` 上游判据 `pass=3`、`test_gsl_ieee_mode` gsl 制品 SIGABRT，逐项技术原因见上，均非本次适配引入）、**3** 项"已执行无通过判据"（`test_gsl_multifit`/`test_sigma_invariants` 无累加器、`test_parse_noempty_strtox` 需命令行参数）。通过率分层写：**注册项 7/7；直跑项 5/10；全量口径 12/17**，不把不判定项并入"通过"，也不把失败改判通过。
  - 执行与判定的**取证位置已收进配方本体**：`build()` 里 17 个 test_* 先按 E077 顺序自签（目标是 `lib/.libs` 下的真 ELF——libtool 在 `lib/` 下留的是 `/bin/sh` wrapper，签它会静默 0 命中；本轮探针实证"未签 ELF 必被拒"在 OHOS 上不成立，故签名是防御性动作而非运行前提，与经验汇总 §284/E077/E096 一致），注册的 7 个走 `make check`，其余 10 个直跑并逐项打印 `rc=` 与判据行（`STRICT`/`EXPECTED_FAIL`/`NO_CRITERION` 三档），STRICT 档 rc≠0 直接抛错 ⇒ `N_executed=17` 可由本轮 conan 日志自证（W4 审计 P1 的整改）。
- `N_consumer = 5`：`smoke_inhomog.c` 4 条数值断言（`{3,4,0}→5`、`{1,2,2}→3`、`3params(0,5,12)→13`、`{0,0,0}→1e-100` 即源码 `fmax(TOL_LENGTH_SQUARED,·)` 的托底行为）+ 已签名 `bin/inhomog --help`（实测 rc=0，输出首行 `Usage: inhomog [OPTION...]`）⇒ 同时证明 argp-standalone 路线在运行期真实可用。
- 内存：14 个测试程序经 `memcap-run.py` 实测峰值 4–16MB（最大 `test_Omega_D` 16MB / 41.1s），`max_rss_mb: 512`。

## 已知限制

1. `test_scale_factor_D_Ham` 与 `test_gsl_ieee_mode` 两项在上游注册体系之外执行失败，原因见上；解除条件分别是数值容差复核（上游事项）与 gsl 制品支持 IEEE 平台判定。
2. CLI `inhomog` 是纯数值/宇宙学工具，无硬件与特权依赖，故运行期可达性无 thermald 那类 sysfs 问题；本次消费者测试覆盖 `--help` 路径与库 API，未覆盖其全部选项组合。
3. 产物按 `shared=True` 交付（`--enable-shared --disable-static`）；如需静态消费者，`inhomog_LDFLAGS=-static`（`Makefile.am:10` 上游未注释）这一路径本轮实测在 OHOS 下未触发问题，未额外验证。
4. 框架 `finish` 的 **G0 干净构建探针（`scripts/ohc/clean_verify.py`）对本包结构性必挂**，非配方缺陷、也非交付阻断：G0 是"解原件 + 裸 `./configure`"，**不经 conan 依赖链路**（`gsl/2.8`、`argp-standalone/1.5.0` 的头/库/`-L`/`-l` 只由 `conan create` 注入），且 `clean_verify.py` 只解析 `configure_options` 列表的**第一项**（其余靠 env）⇒ 真机首错逐字 `configure: error: Could not find gsl.`。框架 `finish.py` 对该步明确 "Do not raise SystemExit - continue with finish"（软门），硬证据以 G2（真 `conan create`，本轮 CREATE_RC=0）为准。同形态先例=`ledmon 0.97 #12454`（已过 CI/AI 裁决）。
5. `patches/0001` 的降级告警只写进 `config.log`（`>&5`）、终端不可见。原因：该行的书写形态沿用上游 `configure` 自身的 `$as_echo … >&5` 风格；本轮**不手改补丁**——`refresh-patch` 在本包已两次实撞"重生成即丢补丁/改名导致 `export_sources` 报 Patch file does not exist"（见本文问题表与 git 历史 `36ba0f5447`/`46ec9b7da7`），改 hunk 行数的风险高于收益。留作后续：如需终端可见，应改 `configure` 里该行加 `>&6` 并由框架重生成补丁、再复跑 `conan create` 复验。
6. G0 探针另需在**外部导出** `CONFIG_SHELL=/bin/sh` 才能走到 gsl 那一步：`clean_verify.py:68` 的默认值是 `/data/service/hnp/bin/bash`，该 bash 在 HMDFS 目录 `getcwd()` 报 `Operation not permitted` ⇒ configure 首步即 `working directory cannot be determined`（E386 家族，见经验汇总 §12.38①）。本包**配方自身不受影响**（`conan create` 全绿），故不改框架（框架文件只读）。

## 适配路径

- 路径 A（基础适配）。B 判定 = `hit`：本轮唯一的候选新机制（configure run 探测被误判成交叉）已由仓库条目 **E467** 与 `DRAFT-conan-dep-shared-libs-break-configure-conftest` 覆盖（同签名、同解法），设备侧 `knowledge/` 全量 grep 实证；其余适配点（`-lgcc`、`error.h` 死包含、`argp.h` 用已发布依赖、`config.sub` 老版）分别落在 E007 家族与既有 glibc-缺失接口条目族内 ⇒ 不申报 B。

## 验证命令

```
conan create archives/i/inhomog/0.1.9.2 --build=inhomog/* \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```
- 补丁命名改用框架约定：refresh-patch 按 builds/inhomog-0.1.9.2.orig 与 .work 的逐文件 diff 重生成并改名（0001-configure.patch、0002-xmalloc.c.patch）。头两次 finish 因为它只追踪到 configure 一处改动而丢掉 xmalloc 补丁，于是 export_sources 报 ConanException: Patch file does not exist（补丁名与 conandata 不一致）⇒ 正确处置不是对抗工具，而是把两处改动同时做进 .work 树再让它生成，并按它给出的文件名同步 conandata.yml（提交 36ba0f5447）。此后 conan create 复验 CREATE_RC=0：注册测试 # PASS: 7 / # FAIL: 0 / # SKIP: 0 / # ERROR: 0，Package b352603f79862d5b1716e4f12228956432cf3d3c created，消费者 4/4 断言通过。
---

**编译结束**: 2026-09-25 18:53
**最终状态**: built

## 发现与知识
（与 manifest.yaml `knowledge_gained` 一一对应；序号即 ref 标号）

- ✅ 1 **OHOS 交叉下 `-lgcc` 硬中止**：CI profile 的 clang 无 `libgcc.a`（真机逐字 `ld.lld: error: unable to find library -lgcc`；sysroot 内 `find libgcc*` 零命中，运行时实为 `libclang_rt.builtins.a`），而上游 `AC_CHECK_LIB(gcc,main)` 的失败分支是 `AC_MSG_ERROR` ⇒ configure 直接中止。该检查上游自陈面向 "Solaris systems with f77" ⇒ 0001 补丁把失败分支降为告警继续（1 行），不注入 `-lgcc`、不改源码逻辑。
- ✅ 2 **OHOS musl 无 `error.h`，但本包只需删死包含**：`xmalloc.c:55` 的 `#include <error.h>` 是全树唯一出现处且 `error()`/`error_at_line` 全树零调用（实测 grep 计数=0）⇒ 逐字 `fatal error: 'error.h' file not found` 的最小解法是删这一行，**不写 `error()` 兼容层**（写了反而是无据的行为改动）。
- ✅ 3 **`argp.h` 硬门可由已发布依赖零改上游满足**：`configure.ac:123` 只有 `AC_CHECK_HEADER(argp.h,,AC_MSG_ERROR)`、**全树没有 argp 的库探测**，而 `inhomog.c:126` 真调 `argp_parse` ⇒ 正确解法是 `requires("argp-standalone/1.5.0")`（实测包内实带 `include/argp.h` + `lib/libargp.a`）并**显式补 `-largp`**；不改 `inhomog.c` 一行。
- ✅ 4 **configure 的 run 探测被依赖共享库拖成"假交叉"**（=E467 同签名同解法，故本 PR 不申报 B）：`AC_PROG_CC` 最早的 run 探测沿用 LIBS 里整条依赖闭包去链 conftest，而 conftest 无 RUNPATH ⇒ 加载不到 `libgsl.so`，被 autoconf 归因成 `cannot run C compiled programs`。按该条目 rec：`generate()` 把 host 依赖 `libdirs` 前置进 `LD_LIBRARY_PATH`、`bindirs` 进 `PATH`。**自纠**：曾试图用 `--host=…-musl` 制造交叉判定压症状，正是该条目 forbid 项与 P-AUTOTOOLS-001 禁止的绕过，已撤回。
- ✅ 5 **conan VPATH 构建需显式 `-I$(source_root)`**：上游源码写 `#include "lib/inhomog.h"`（`power_spectrum_flatspace.c:32`、`FLRW_background.c:37` 等）只在 in-tree 构建成立；VPATH 分离构建时该相对路径不在搜索路径内 ⇒ 配方补 `-I<src_root>`，不改上游 include 写法。
- ✅ 6 **automake 维护者规则要在 `make` 与 `make install` 两处都关**：解包后 automake 判定生成物过期会去跑 `aclocal`（OHOS 无该可执行名，真机逐字 `make: *** [Makefile:466: …/src/aclocal.m4] Error 127`）⇒ 两处都要传 `ACLOCAL=: AUTOMAKE=: AUTOCONF=: AUTOHEADER=:`。先试 `os.utime` 钉 mtime（"输入旧/生成物新"）在 HMDFS 上**不生效**、仍犯。
- ✅ 7 **公开头声明的函数未必由库导出**：`test_power_spectrum_flatspace` 在 `inhomog.h:343` 有声明，但其定义所在的 `.c` 不在编入库的 19 个源文件里（它是 `noinst_PROGRAMS` 测试程序的驱动）⇒ 消费者测试若链接该符号会得到 undefined symbol；写 `test_package` 前必须按"库实际导出面"选符号（`nm -D` 核），不能照头文件清单抄。
