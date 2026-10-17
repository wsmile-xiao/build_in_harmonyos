# libgtop2 2.41.3 适配笔记

## 基本信息

| 项 | 值 |
|---|---|
| 上游仓库 | https://gitlab.gnome.org/GNOME/libgtop |
| tag / commit | `2.41.3` / `526a51698173535312f6cab1408ac9a225063c9d` |
| 官方源码 | https://download.gnome.org/sources/libgtop/2.41/libgtop-2.41.3.tar.xz |
| sha256 | `775676df958e2ea2452f7568f28b2ea581063d312773dd5c0b7624c1b9b2da8c`（754028 B） |
| 构建系统 | autotools（tarball 内含预生成 `configure`；**无 meson.build**） |
| 源码语言 | C（408 个源文件，主体占比 100%）→ R47 语言预检 `detected=c`，与任务语言 cpp 同族，无需迁移 |
| 对外产物 | `libgtop-2.0.a`（默认静态）、`include/libgtop-2.0/`、`lib/pkgconfig/libgtop-2.0.pc`、`libexec/libgtop_daemon2`、`libexec/libgtop_server2`、`share/info/libgtop2.info`、87 个 locale `.mo` |

## 编译环境

- 编译日期：2026-09-21
- 编译器：clang 15.0.4（`/data/service/hnp/bin/clang`），target `aarch64-unknown-linux-ohos`
- Conan：2.29.1；profile `ohos-aarch64`（os=OHOS, os.version=6.0, arch=armv8, compiler=clang/15, libc++, Release）
- 运行内核：`HarmonyOS / HongMeng Kernel 1.12.0 (aarch64)`

## 依赖（来自上游 configure.ac / Makefile.am 的真实判据）

| 依赖 | 版本 | 类型 | 判据 |
|---|---|---|---|
| glib（`glib-2.0` / `gobject-2.0`） | 2.88.3 | 直接·强制 | `configure.ac:107` `PKG_CHECK_MODULES(GLIB, glib-2.0 >= 2.6.0 gobject-2.0 >= 2.26.0)`；`lib/Makefile.am:11` `LIBADD=$(GLIB_LIBS)`；`libgtop-2.0.pc.in:6` `Requires: glib-2.0`；`glibtop.h:29-30` 直接 include `glib.h`/`glib-object.h`（头文件传染） |
| proxy-libintl | 0.5 | 直接·强制（ngettext） | `lib/read.c:49`（及 `write.c:49`、`read_data.c:66`）经 `<glib/gi18n-lib.h>` 使用 `ngettext()`；见下 F5 |
| pkgconf | 3.0.6 | 构建工具 | `configure.ac:107` `PKG_CHECK_MODULES` 需要 pkg-config |

已确认**不需要**：`libxt` / `libxau`（配方 `--without-x`）、`gobject-introspection`（`--enable-introspection=no`）、`gtk-doc`、`texinfo`（见 F4）。

## 编译步骤（真实命令）

```bash
# 1) 依赖环境（clean CONAN_HOME + ohpcd，等价于配方内 PkgConfigDeps 生成物）
conan install --requires=glib/2.88.3 --requires=proxy-libintl/0.5 \
    -r=ohpcd -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=never \
    -g PkgConfigDeps -g AutotoolsDeps

# 2) 补丁 + configure（补丁由 refresh-patch --auto 从 track-edit 差异生成）
patch -p1 < patches/0001-config.guess.patch
patch -p1 < patches/0002-config.sub.patch
patch -p1 < patches/0003-configure.patch
#   补丁后还原 configure 的 mtime（见 F4）
PKG_CONFIG_PATH=<generators> ./configure --prefix=$DEFAULT_PREFIX \
    --without-x --enable-introspection=no --with-examples=yes \
    --enable-static --disable-shared
make -j2
make install DESTDIR=$TEST_PREFIX
```

最终以 `conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 -r=ohpcd` 一次通过（exit 0，含 test_package）。

## 遇到的问题与解决方案

| # | 现象（首个真实错误） | 根因 | 解决方案 |
|---|---|---|---|
| F1 | `checking build system type... ./config.guess: unable to guess system type` → `configure: error: cannot guess build type; you must specify one`（exit 1） | 上游 tarball 自带 `config.guess`(2023-06-23) 无 HarmonyOS 分支，`uname -s=HarmonyOS` 无法匹配（E007） | `patches/0001-config.guess.patch`：按 `UNAME_SYSTEM=HarmonyOS` 输出 `aarch64-unknown-linux-ohos` |
| F2 | `./config.sub: Invalid configuration 'aarch64-linux-ohos': Kernel 'linux' not known to work with OS 'ohos'.`（exit 1） | `config.sub` 不认 `ohos` 作 OS，且 kernel-os 白名单缺 `linux-ohos*`（E072）。注意 `patch-autotools-ohos.pl` 的"linux-ohos already present"是误判（命中的是 `basic_os=linux-ohos`），第 3 处需人工补 | `patches/0002-config.sub.patch`：`ohos-linux` 映射 + OS 白名单 `ohos*` + kernel-os 白名单 `linux-ohos*` |
| F3 | `./conftest: Error loading shared library libgirepository-2.0.so.0 ...` → `configure: error: cannot run C compiled programs`（exit 77） | configure 需真正运行 conftest，而 glib 的 .so 不在加载器搜索路径 | 探索阶段：`source conanrun.sh` 引入 `LD_LIBRARY_PATH`；配方阶段由 Conan 的 `Autotools` 助手（`conanbuild` 环境）承担 |
| F4 | `configure: error: Package requirements (glib-2.0 >= 2.6.0 gobject-2.0 >= 2.26.0) were not met: No package 'glib-2.0' found`（exit 1） | `PkgConfigDeps` 生成的 `.pc` 落在 generators 目录，未进入 `PKG_CONFIG_PATH` | 配方 `generate()` 以 `PKG_CONFIG_PATH=<generators_folder>` 形式传给 configure（本仓 autotools 惯例） |
| F5 | `config.status: line 846: ./conflKEBhL/subs1.awk: Permission denied` → `config.status: error: could not setup config files machinery`（exit 1） | autoconf 2.70+ 的 `config.status` 用 `(umask 077 && mktemp -d "./confXXXXXX")`；HMDFS 上 umask 077 产出的目录当前进程不可写（E011）。实测：`umask 077 + mktemp -d` → `drwx--S---`，写入 `Permission denied`；`umask 022` → 可写 | `patches/0003-configure.patch`：`umask 077` → `umask 022`（2 处） |
| F6 | `read.c:49:5: error: incompatible integer to pointer conversion passing 'int' to parameter of type 'const char *'`（`ngettext` 隐式声明为 int） | `lib/read.c` 经 `<glib/gi18n-lib.h>`（无条件 `#include <libintl.h>`）用 `ngettext()`；编译时命中的是 **OHOS SDK sysroot 的空壳 `/…/sysroot/usr/include/libintl.h`**（`grep ngettext` 无任何声明） | 把 `proxy-libintl/0.5` 提为**直接依赖**：PkgConfigDeps 会在生成的 `glib-2.0.pc` 中补 `Requires: intl`，proxy-libintl 的 `libintl.h`（`#define ngettext g_libintl_ngettext`）随 `GLIB_CFLAGS` 进入编译行即修复；符号 `g_libintl_*` 已被静态链接进 `libglib-2.0.so`（`llvm-nm -D` 实测导出），无需额外链接参数 |
| F7 | `make install` 在 `doc/` 报 `MAKEINFO libgtop2.info` → `missing: line 81: makeinfo: command not found` → `Error 127`，`install-recursive` 中断（顶层 `libgtop-2.0.pc`、`glibtop.h` 未安装） | ① OHOS 无 texinfo(makeinfo)；② 打补丁刷新了 `configure` 的 mtime，使 `doc/stamp-vti`（依 `$(top_srcdir)/configure`）判过期 → 连带 `version.texi`/`libgtop2.info` 走 texinfo 链；③ `doc/mdate-sh` 在本平台解析 `ls -L -l -d -n` 失败，`set \`…\`` 无输出时 `set` 打印全部 shell 变量 → `version.texi` 被写成 6094 B 的环境转储（原 103 B） | 配方 `build()` 在 `apply_conandata_patches()` 前后记录/还原 `configure` 的 mtime（`os.stat` + `os.utime`）→ `stamp-vti` 判定不过期 → 复用上游随包发布的 `doc/libgtop2.info`，全程不调用 makeinfo。实测在**纯净 tarball + 3 个补丁**上 `configure/make/make install` 均 exit 0 |

## 源码修改（补丁）

| 补丁 | 目标 | 内容 |
|---|---|---|
| `0001-config.guess.patch` | `config.guess`（+11/−0） | 新增 `*:HarmonyOS:*:*` 分支，按 `UNAME_MACHINE` 输出 `aarch64/arm/x86_64/i686-unknown-linux-ohos` |
| `0002-config.sub.patch` | `config.sub`（+6/−2） | ① `ohos-linux) → basic_os=linux-ohos`；② OS 白名单加 `ohos*`；③ kernel-os 白名单加 `linux-ohos*` |
| `0003-configure.patch` | `configure`（+2/−2） | `config.status` 模板中的 `umask 077` → `umask 022` |

> 三个补丁均属**平台可移植性**类，无 `__OHOS__` 平台宏（满足 R8/PF5）——`config.guess`/`config.sub` 是上游多平台共用的探测脚本，新增的是随宿主 `uname` 走的标准分支。

## 上游测试（R51 三步法）

**第一步 · 清点**（真实命令与输出）

```bash
find . -type d -iname '*test*'                              # 无输出（无 tests/ 目录）
grep -rn 'check_PROGRAMS|^TESTS' --include=Makefile.am .     # 无匹配，rc=1
grep -n 'noinst_PROGRAMS' examples/Makefile.am               # 20 个样例程序
```

→ **上游无自动化测试套件**（`make check` 无内容），唯一可运行入口是 `examples/` 的 20 个样例。

**第二步 · 实际运行**（`LD_LIBRARY_PATH=<build>/lib/.libs`，逐项 timeout 运行）

| 结果 | 数量 | 样例 |
|---|---|---|
| 通过（exit 0） | **19** | first, second, pprint, procargs, df, netlist, mountlist, procmap, netload(`wlan0`), sysdeps, timings(约 60s), openfiles, smp, proclist, free, wd, affinity, diskio, sysinfo |
| 失败（exit 134） | **1** | `disk` —— `glibtop_get_disk()` 读 `/proc/diskstats` 返回 EACCES |
| 跳过 | 0 | —— |

日志（本地构建产物，`reports/` 被仓库 `.gitignore` 忽略，不随 PR 提交）：
`reports/upstream-examples-run.log`、`reports/upstream-examples-exitcodes.log`。
`disk` 失败取证：`ls -l /proc/diskstats → lr--r--r-- root root … -> /sys/block/diskstats`，`cat /proc/diskstats` 与 `cat /sys/block/diskstats` 均 rc=1（Permission denied）→ **OHOS 平台限制**（libgtop 的 disk/mount 采集本应由 setuid 辅助进程 `libgtop_server2` 完成，OHOS 不可 setuid），非适配缺陷。

**第三步 · 回填**：见 `test_package/MANIFEST.yml`（20 个样例逐项列出）与本文件。

## 验证结果

```bash
$ conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 -r=ohpcd
...
libgtop2/2.41.3: package(): Packaged 43 '.h' files
libgtop2/2.41.3: package(): Packaged 1 '.a' file: libgtop-2.0.a
libgtop2/2.41.3: package(): Packaged 1 '.pc' file: libgtop-2.0.pc
libgtop2/2.41.3: package(): Packaged 3 files: libgtop_daemon2, libgtop_server2, COPYING
libgtop2/2.41.3: Package 'b7306ef6d7141b8d0bcdffecb22f814830b6bdde' created
exit_code=0

# test_package（2/2 通过）
1/2 Test #1: test_libgtop2_api ................   Passed    0.09 sec
2/2 Test #2: test_libgtop2_ohos ...............   Passed    0.06 sec
100% tests passed, 0 tests failed out of 2
PASS: glibtop_get_cpu(): total ticks > 0
PASS: glibtop_get_mem(): total bytes > 0
PASS: glibtop_get_uptime(): uptime > 0
PASS: glibtop_get_sysinfo(): ncpu > 0
libgtop2 2.41.3: ncpu=20 mem_total=33464987648 uptime=22304s
kernel: HarmonyOS HongMeng Kernel 1.12.0 (aarch64)
PASS: OHOS: /proc/stat per-cpu ticks readable
PASS: OHOS: sysinfo ncpu >= 1
PASS: OHOS: /proc process table enumerable
OHOS: proclist number=258
```

## 交付物

| 文件 | 说明 |
|---|---|
| `libgtop-2.0.a` | 静态库（默认 `shared=False`） |
| `include/libgtop-2.0/` | 43 个头文件（`glibtop.h`、`libgtopconfig.h`、`glibtop/*.h`） |
| `lib/pkgconfig/libgtop-2.0.pc` | 上游 pkg-config 模块（`Requires: glib-2.0`） |
| `libexec/libgtop_daemon2`、`libexec/libgtop_server2` | 上游辅助进程（特权采集，OHOS 上不可 setuid，未做 setuid 安装） |
| `share/info/libgtop2.info`、`share/gtk-doc/html/libgtop/*` | 上游随包文档 |

## 注意事项

1. **默认静态**（`shared=False`）：本库非系统同名库，但静态可绕开 OHOS 上"未签名 .so 被加载器拒载"的额外处理链；如需动态，`conan create -o libgtop2/*:shared=True`，并需在 `package()` 中补 `binary-sign-tool` 签名（本 PR 未引入该分支）。
2. **运行时依赖 Linux procfs**：`sysdeps/linux/` + `src/` 共 139 处 `/proc` 引用（`/proc/stat`、`/proc/meminfo`、`/proc/<pid>/…`）。OHOS 内核兼容该接口，实测 `ncpu=20`、进程表 258 项可正常枚举。
3. **受限项（平台，非配方问题）**：`/proc/diskstats`（→`/sys/block/diskstats`）对非 root 不可读 → `examples/disk` 失败；`libgtop_server2` 的 setuid 安装（`libgtop-sysdeps.m4:39`）在 OHOS 上不成立。
4. `libgtop_daemon2` / `libgtop_server2` 装在 `libexec/`，非 CLI 工具，故软件级目录**不提供** `commands.json`（R38）。
---

## 对话记录

### 对话 #1 — 阶段一：依赖清单分析（只读，不编译）
- 目标：确认 libgtop2/2.41.3 的强制第三方依赖并在制品仓实测可消费。
- 动作：从上游 `configure.ac` / `Makefile.am` / `libgtop-2.0.pc.in` 提依赖；对 23 个依赖
  `conan download -r=ohpcd --only-recipe`（干净 `CONAN_HOME`）逐个探测 + 2 个负向对照；
  `conan install --requires=… --build=never` 权威复核。
- 结果：23/23 `exit 0`，负向对照 `exit 1`；强制第三方依赖缺口 0。
- 产物：`libgtop2-2.41.3-deps/DEPENDENCY-REPORT.md`。

### 对话 #2 — W1 同步 main + worktree/分支
- `git fetch origin main` → `origin/main = 42a8cc8fd8`；`git worktree add libgtop2-2.41.3-wt -b feat/libgtop2-2.41.3 origin/main`（exit 0）。

### 对话 #3 — 源码核验 + init-build + 语言预检
- sha256 `775676df…` 与官方一致（754028 B）；tag `2.41.3` = `526a5169…`。
- `init-build`：errors=0，warnings=3；`lang-preflight`：`task=cpp, detected=c`（同族）。
- 上游测试入口清点：无 `tests/`、无 `check_PROGRAMS/TESTS` → 无自动化测试套件。

### 对话 #4 — 首次 configure 失败（F1/F2）与三元组修复
- 首个真实错误：`config.guess: unable to guess system type` → `configure: error: cannot guess build type`（exit 1）。
- 根因：上游 config.guess(2023-06-23) 无 HarmonyOS 分支（E007）；config.sub 不认 `ohos` 且 kernel-os 白名单缺 `linux-ohos*`（E072）。
- 修复：`patch-autotools-ohos.pl` + 手工补 config.sub 第 3 处（脚本 "already present" 系误判）。
- 重验证：`./config.sub aarch64-linux-ohos` → `aarch64-unknown-linux-ohos`（exit 0）。

### 对话 #5 — conftest / pkg-config / config.status 失败（F3/F4/F5）
- F3：`cannot run C compiled programs` → 构建期需 conan 运行环境（`LD_LIBRARY_PATH` 含 glib 包）。
- F4：`No package 'glib-2.0' found` → `PKG_CONFIG_PATH=<generators>`。
- F5：`config.status: … subs1.awk: Permission denied` → HMDFS 上 `umask 077 && mktemp -d` 目录不可写（E011）→ 改 `umask 022`。

### 对话 #6 — 编译通过（F6 ngettext）与安装通过（F7 texinfo）
- F6：`read.c:49 incompatible integer to pointer conversion`（`ngettext` 隐式 int）——命中的是 OHOS SDK sysroot 的空壳 `libintl.h`。
  修复：把 `proxy-libintl/0.5` 提为直接依赖 → Conan 生成的 `glib-2.0.pc` 带 `Requires: intl` → 正确的 `libintl.h` 进入编译行。
- F7：`make install` 在 `doc/` 调 makeinfo（不存在）失败，且 `mdate-sh` 解析失败把 `version.texi` 写成环境转储。
  修复：补丁前后记录/还原 `configure` 的 mtime → 复用上游随包 `libgtop2.info`。
- 重验证：`configure/make/make install` 全 exit 0；`make -j2` 产出 20 个样例。

### 对话 #7 — 上游测试实际执行 + 配方与 test_package
- 逐项运行 20 个样例：19 PASS / 1 FAIL（`disk`，`/proc/diskstats` EACCES）；`netload` 需网卡参数（`wlan0`/`lo` 均 PASS）；`timings` 约 60s。
- `conan-init` 生成骨架 → 补齐 conanfile.py / conandata.yml / manifest / notes / test_package（含 1 个鸿蒙特有用例）。
- `conan create`（首次）：构建与打包成功，`package_info()` 报 "direct dependency 'proxy-libintl' is not used by any requires" → 补 `proxy-intl::proxy-libintl` 到 `cpp_info.requires`；第二次 `conan create` exit 0（test_package 2/2）。

### 对话 #8 — conan-verify / finish / W2-W3 / 文件原子性
- `conan-verify`：G0–G4 全 PASS（L2/L4/L5 因取不到包缓存路径而跳过）；另加 E490 建议的 autotools 脚本可执行位守卫。
- `finish built`：W3 本地 CI 首轮被 JC1/JC5 拦截，拦截对象是 **origin/main 中既有的
  `archives/c/cloog/0.21.1/.build-closed`、`archives/c/cloog/0.21.1/.staging-verified`、
  `archives/k/kics/2.1.20/.staging-verified`**（非本任务产物；因本任务按约定不 commit，
  junk_check 退化为整仓 full 模式才扫到）。以 CI 的 PR-diff 模式（`JUNK_PR_DIFF`）重跑，W3 通过（JC 0 项、单软件原子性合规）。
- 文件原子性：PR 等价白名单 13 个文件，全部位于 `archives/l/libgtop2/`。
- 待处理（提交前）：`conandata.yml` 被本地 CI 预下载逻辑写回镜像列表，须还原为"仅官方源"形态。

状态：built
---

**编译结束**: 2026-09-21 03:05
**最终状态**: built
