# librcd 0.1.14 — 适配笔记

> 建档：2026-09-15 ｜ 任务：开源鸿蒙PC专项积分赛 ｜ 分支 `feat/librcd-0.1.14`
> 本包是**新包**（`archives/l/librcd/` 在 `upstream/main` 不存在），首次适配。

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | librcd（R. Charset Detection Library，RusXMMS 项目） |
| 版本 | 0.1.14 |
| 状态 | built（conan create 通过；未合并/未走 release 上传，故不标 published） |
| 构建系统 | autotools（autoconf 2.68 + libtool 2.4.2；configure/ltmain.sh/m4 均随包预生成） |
| 源码 | https://deb.debian.org/debian/pool/main/libr/librcd/librcd_0.1.14.orig.tar.bz2 |
| sha256 | 261db28bc864fd4b2d3ba88403b2e421944281e323c1e39c0e61f5160c16b664（308041 字节） |
| 许可证 | LGPL-2.1-or-later（`COPYING` = LGPL-2.1；源码头文件写 "version 2.1 or later"） |
| 依赖 | 无第三方依赖（W0 空集，见 `$HOME/tmp/librcd-0.1.14/w0-deps.txt`） |
| 平台 | OHOS aarch64（`ci/conan/profiles/ohos-aarch64`，clang 15.0.4，Release） |

## 二、上游调查

- 上游主页 `http://rusxmms.sourceforge.net/`、发布机 `dside.dyndns.org` 均已下线
  （实测 `http://dside.dyndns.org/files/rusxmms/librcd-0.1.14.tar.bz2` 无响应）；
  源码镜像 `https://github.com/RusXMMS/librcd`（master，2021-03-12，无 tag/release）。
  本包取 **Debian 源码包的 pristine 上游归档**（`Format: 3.0 (quilt)`、
  `Version: 0.1.14-1`、无 dfsg 重打包）——`sha256` 与 `librcd_0.1.14-1.dsc` 的
  `Checksums-Sha256` 逐字一致，属 R39 认可的权威镜像源（本仓库大量配方同用
  deb.debian.org 的 pool 源，例如 a52dec/0.7.4、aalib/1.4p5、abook/0.6.1）。
- 上游内容（tarball 共 54 个 tar 条目 = 48 个文件 + 6 个目录）：`configure`/`configure.ac`/`Makefile.am`、`src/`（`librcd.c`
  339 行 + `russian_table.h` 899 行数据表 + `librcd.h`）、`examples/`（演示程序）、
  `statgen/`（离线语料统计/表生成工具）、`m4/` + `ltmain.sh` + `aclocal.m4`（libtool
  2.4.2 宏与脚本，已预生成）、`CMakeLists.txt`（**Windows 专用**，首行
  `FATAL_ERROR "Windows only, use autotools to build under POSIX-capable systems"`）。
- 唯一公开 API：`rcdGetRussianCharset(const char *buf, int len)`，返回
  `rcd_russian_charset`（0=CP1251 / 1=KOI8-R / 2=UTF8 / 3=CP866 / 4=ISO8859-1）。
- 上游测试：**无自动化套件，N = 0**（清点与归因见第六节）。
- 产物（shared=True）：`lib/librcd.so.0.1.14` + `librcd.so.0`/`librcd.so` 软链
  （soname `librcd.so.0`）、`include/librcd.h`、`lib/pkgconfig/librcd.pc`。
  **注意**：`librcd.pc` 的 `Libs:` 是 `-lrcd`（链接 `librcd.so`，automake 直接用
  `librcd.la` 的基名），故配方声明 `cpp_info.libs = ["rcd"]`。

## 三、编译步骤

```sh
# 采信轮实际入口（容器层工具：清缓存 → conan-verify → 证据副本 → finish 前快照）
sh "$HOME/ws/tools/conan_verify_round.sh" librcd 0.1.14 \
   --repo "$HOME/ws/worktrees/librcd-0.1.14" --task-dir "$HOME/tmp/librcd-0.1.14"

# 等价的手工复现（探索期实测命令）
conan create archives/l/librcd/0.1.14 \
  -pr:h=<repo>/ci/conan/profiles/ohos-aarch64 -pr:b=<repo>/ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable -c tools.build:jobs=2
```

与仓库 autotools 模板的差异只有三处，都有理由：①`options.shared` 显式二选一
（`--enable-shared --disable-static` / 反之），因为上游 libtool 默认同时产出 `.so`
与 `.a`；②`make` 用 `-j1`（仓库 582 处同款，避免 `os.cpu_count()`=20 与容器
affinity=8 的超订）；③OHOS 上 configure 用 `CONFIG_SHELL=/system/bin/sh
SHELL=/system/bin/sh /system/bin/sh <srcdir>/configure ...` 显式执行（见问题 5）。

**不做 autoreconf**：`configure`/`config.sub`/`config.guess`/`ltmain.sh`/`m4/*.m4`/
`aclocal.m4` 都是随包分发的预生成物，因此不依赖 worker 上缺失的 automake
（设备 harmonybrew 有 automake 而 worker PATH 没有，属已知假绿源）。

## 四、遇到的问题与解决方案

| # | 问题（逐字现象） | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: cannot guess build type; you must specify one`；`./config.guess: unable to guess system type`（`uname -s` = `HarmonyOS`） | 上游 `config.guess` 时间戳 2005-03-24，`case "${UNAME_MACHINE}:${UNAME_SYSTEM}:..."` 里没有 HarmonyOS 分支，落到 `*)` 的 "unable to guess" 兜底 | 补丁 `0002-config.guess-harmonyos.patch`：在 UNAME_* 取值后对 `aarch64:HarmonyOS`/`aarch64:Linux` 直接 `echo aarch64-unknown-linux-gnu; exit 0`。**必须短路**而不是只给 LIBC 探测加 HarmonyOS：该探测要在 `(umask 077 && mktemp -d "$TMPDIR/cgXXXXXX")` 建的目录里编译探针程序，OHOS 沙箱里创建者自己都写不进去（见问题 3），`LIBC` 会退化成空串 |
| 2 | 直接给 triplet 时 `Invalid configuration 'aarch64-linux-ohos': machine 'aarch64-linux' not recognized`（`aarch64-linux-gnu` 同样报 `machine 'aarch64' not recognized`） | 同年代的 `config.sub` 的机器表里没有 `aarch64`，OS 表里没有 `linux-ohos` | 补丁 `0001-config.sub-aarch64-ohos.patch`：机器表加 `aarch64`，两处 OS 表加 `linux-ohos*`（仓库先例 `archives/a/aalib/1.4p5`、`archives/a/a52dec/0.7.4`） |
| 3 | `config.status: error: cannot create a temporary directory in .`（或 `mktemp` 目录后续 `touch: Permission denied`） | autoconf 2.68 的 config.status 用 `(umask 077 && mktemp -d "./confXXXXXX")`；HMDFS 把 0700 目录落成 `drwx--S--- 2700` 且属主映射为共享属主 `20001006`（进程 euid 是另一个号），**创建者自己随后也写不进去**。实测：`umask 077` → `drwx--S--- 2700` + `touch FAIL: Permission denied`；`umask 022` → `drwxr-s--x 2751` + `touch OK` | 补丁 `0003-configure-config-status-umask.patch`：两处 `umask 077` → `umask 022`（同款先例 `archives/a/alsa-lib/1.2.16.1`、`archives/a/a52dec/0.7.4`；知识条目 E011/E136） |
| 4 | `src/Makefile` 里 `librcd_la_LDFLAGS = -version-info 0:0:0`，产物名 `librcd.so.0.0.0`（上游应为 `1:14:1` / `librcd.so.0.1.14`） | 上游 `configure.ac` 用 shell 命令 `LIBRCD_VERSION_MAJOR=\`cat VERSION \| ...\`` 取版本号，**相对于当前目录**；conan 的 `Autotools` 固定做 VPATH 构建（`configure` 在 `build-release/` 下执行），那里没有 `VERSION` → 三项都取空 → `sed s/^$/0/` 补成 0 → `LIBRCD_VERSION_INFO=0:0:0`。（`librcd.pc` 的 `Version:` 用的是 autoconf 烘进 configure 的 `@VERSION@`=0.1.14，所以只有 libtool 版本号受影响） | 补丁 `0004-configure-read-version-from-srcdir.patch`：`cat VERSION` → `cat "$srcdir/VERSION"`。修复后实测 `-version-info 1:14:1`、`librcd.so.0.1.14`；soname 两种情形下都是 `librcd.so.0`，即 ABI 名不变、只有实体文件名回正 |
| 5 | `../libtool: line 350: syntax error near unexpected token '}'`（出错行是 `echo "local: *; };" >> $output_objdir/$libname.ver~`），同时伴生 `./config.status: line 723: print: command not found` 与 `#  - Provide generalized library-building support services.`（`libtool` 第 2 行丢了 `libtool` 一词） | 两个 shell 的能力错配：conan 调 configure 时它由 shebang 在 **Toybox `/bin/sh`** 下执行（Toybox 自带 `print` 内建，实测 `print -r -- hello` rc=0），autoconf 2.68 因此把 `ECHO` 定为 `print -r --` 并**写死进 config.status**；而 profile `[buildenv]` 把 `CONFIG_SHELL`/`SHELL` 指向 `/data/service/hnp/bin/bash`，configure 的 `SHELL=${CONFIG_SHELL-/bin/sh}` 于是把 bash 烘进 config.status 的 shebang 与 Makefile 的 `SHELL=`，config.status/libtool 随后在 **bash** 里执行 → `$ECHO` 找不到 `print` → libtool 的 "Double-quote double-evaled strings" 段（config.status:715-730）整段失效 → 生成的 `libtool` 丢掉 `\"` 转义、本身成为非法 sh。diff 与原生（非 conan）成功构建的同名文件对照，差异只在转义层：`archive_expsym_cmds="echo \\\"{ global:\\\" ..."`（成功）vs `archive_expsym_cmds="echo "{ global:" ..."`（失败） | 配方 `build()` 的 `_configure()`：OHOS 上用命令行前缀 `CONFIG_SHELL=/system/bin/sh SHELL=/system/bin/sh` + `/system/bin/sh <srcdir>/configure`（命令行赋值优先于聚合 env，可胜过 profile buildenv），把 configure → config.status → Makefile 的 `SHELL` → libtool 全程钉在同一个 shell 上。**不改上游文件**；仓库先例 `archives/a/abx/0.1`、`archives/b/barvinok/0.41.9`、`archives/n/nut/2.8.5`、`archives/b/bluefish/2.2.16`、`archives/c/cyrus-sasl/2.1.28.1`；知识草稿 `DRAFT-E551-ohos-conan-configshell-bash-libtool-escaping` 记的正是这条。原始 conan 失败日志在设备 inode 清理时被删除，同设备可复现的重放证据（逐字输出 + 机制前提实测 + 正对照）见 `reports/shell-mismatch-repro.md` |
| 6 | 单次编译 clang 汇总 `14205 warnings generated`（`warning: illegal character encoding in character literal [-Winvalid-source-encoding]`） | `src/russian_table.h` 是上游生成器按 **KOI8-R/CP866 原始字节**写出的数据表（276238 字节里 14202 个高位字节），整个文件不是合法 UTF-8 | **不掩警告**（仓库先例 `archives/v/vitetris/0.59.1` 亦如实保留）：警告的关键是"字节值有没有被改写"。clang 对窄字符字面量的非法 UTF-8 字节保留原始值，但这一点**必须实证**——否则会出现"编译零错误、检测全错"的假绿。实证方式即 `test_package` 的 34 项断言：CP1251/KOI8-R/CP866/UTF-8 四种编码的同一段俄文与 ISO-8859-1 拉丁文判定全部正确 |

## 五、依赖版本

无第三方依赖（W0 空集成立）。依据三条（全文见 `$HOME/tmp/librcd-0.1.14/w0-deps.txt`）：
①`configure.ac` 无 `AC_CHECK_LIB`/`AC_SEARCH_LIBS`/`AC_CHECK_HEADER`/`PKG_CHECK_MODULES`，
依赖检查只有 `AC_PROG_CC`/`AC_PROG_INSTALL`/`AM_PROG_LIBTOOL` 与 `AC_C_CONST`；
②被构建的 `src/librcd.c` 只 `#include <stdio.h> <string.h> ../config.h librcd.h
russian_table.h`，`librcd.h` 无 include；③`src/Makefile.am` 的 `lib_LTLIBRARIES =
librcd.la` 无 `_LIBADD`/`LIBS`，唯一的 `-lm` 在 `statgen/Makefile.am`（`statgen/` 不在
`SUBDIRS`，不参与构建）。

## 六、上游测试与消费者测试分账

| 口径 | N | 结果 | 依据 |
|------|---|------|------|
| 上游自动化测试（候选数法清点） | **0** | N′=0（无套件可跑，非跳过） | 顶层 `Makefile.am` 只有 `SUBDIRS = src`；四个 `Makefile.am` 全文无 `TESTS`/`check_PROGRAMS`；实测 `make check` → `Making check in src` / `make[1]: Nothing to be done for 'check'.` 后直接返回 0。候选 2（`examples/Makefile.am` 的 `test:` 与 `statgen/Makefile.am` 的 `tests:`）不挂在 `make check` 下、两个目录都不在 `SUBDIRS`、目标体内 0 条断言，`statgen/doit` 还需 `dos2unix`+`iconv`+`ru_RU.KOI8-R` locale 与语料；候选 3（`examples/example.c`、`statgen/test.c`）是演示/工具程序，无断言。逐项归因见 `test_package/MANIFEST.yml` |
| `test_package` 消费者测试（本任务新增，鸿蒙行） | 34 项断言 | 34 PASS / 0 FAIL / 0 SKIP | `test_package/test_librcd.c` 的 `CHECK` 宏输出 `[test_librcd] checks=34 failures=0`；ctest `1/1 Test #1: test_librcd ... Passed` |

> 两类**不混算**：上游 0 项不因消费者测试通过而变成"上游已测"，消费者测试也不计入
> 上游 N。适配后表的合计 = 上游合计 + 鸿蒙行 = 0 + 34。

## 七、源码修改

| 文件 | 补丁 | 内容 |
|------|------|------|
| `config.sub` | 0001 | 机器表加 `aarch64`；两处 OS 表加 `linux-ohos*` |
| `config.guess` | 0002 | 对 `aarch64:HarmonyOS` / `aarch64:Linux` 直接回 `aarch64-unknown-linux-gnu` |
| `configure` | 0003 | `config.status` 临时目录 `umask 077` → `022`（两处） |
| `configure` | 0004 | `LIBRCD_VERSION_{MAJOR,MINOR,SUBMINOR}` 的 `cat VERSION` → `cat "$srcdir/VERSION"` |

**上游 C 源码（`src/*.c`、`src/*.h`）零改动**，不含任何平台宏。此外有一处构建期
shell 钉定（问题 5），只改 conanfile.py，不动上游文件。

## 八、验证结果

```text
# 1) 采信轮（conan-verify G0..G4 + L2/L4/L5）
见 reports/conan-verify-report.md 与 reports/conan-create.log

# 2) conan create（干净源码重建）+ test_package
librcd.so.0.1.14 / librcd.so.0 / librcd.so（soname librcd.so.0）
[test_librcd] checks=34 failures=0
[test_librcd] OK
1/1 Test #1: test_librcd ................   Passed
100% tests passed, 0 tests failed out of 1

# 3) 包内产物（shared=True）
include/librcd.h
lib/librcd.so -> librcd.so.0.1.14
lib/librcd.so.0 -> librcd.so.0.1.14
lib/librcd.so.0.1.14
lib/pkgconfig/librcd.pc      (Version: 0.1.14, Libs: -L${libdir} -lrcd)
licenses/COPYING
```

## 九、注意事项

- **不要在配方里添加 `-Wno-invalid-source-encoding`**：`russian_table.h` 的非 UTF-8
  是上游数据表的既定形态，掩掉警告就失去了"字节值未变"这一观察点；正确做法是用
  消费者断言实证（见问题 6）。
- 系统同名库检查（R26/G3）：设备 `/lib`、`/lib64` 下**不存在** `librcd`，故不触发
  系统同名库静态约束；默认 `shared=True` 由 Conan 管理依赖链。
- 上游 `librcd.pc` 的 `Libs:` 是 `-lrcd`（库文件是 `librcd.so`），`cpp_info.libs`
  必须写 `["rcd"]`；写成 `["librcd"]` 会生成 `-llibrcd` 去找不存在的 `liblibrcd.so`。
- 本包为**新包**（`archives/l/librcd/` 在 `upstream/main` 不存在），建 PR 时按容器层
  口径会命中 PF9 确定性误报，需 `--no-preflight` 并在 PR 正文留痕。
- `statgen/` 的表生成链（`doit` + `generate` + `dragons.txt`）本次未运行：它需要
  `dos2unix`、`iconv` 与 `ru_RU.KOI8-R` locale 才能跑，属离线工具链，与"库本身能否
  在 OHOS 上正确检测编码"无关；库的正确性由 `test_package` 直接断言交付产物承担。
