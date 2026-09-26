# opt 3.19 适配笔记

## 结论速览

| 项 | 实测 |
|---|---|
| 源 | Debian pool `opt_3.19.orig.tar.gz`，sha256 `9feb44c0f9ed88d12b08dab6d3c32da6f0b5094007cc1e6e112d2d53e6435acc`（216621 B） |
| 构建系统 | 随包 `configure`（autoconf 2.13）+ automake 1.4-p5 生成的 Makefile.in，**全程不用 autoreconf** |
| 硬依赖 | **缺集 = ∅**（静态 + 动态双 profile 互证）；readline/termcap 为 `--with-readline` opt-in 可选且默认关 |
| 产物 | 静态库 `lib/libopt.a` + `include/opt.h` + 3 个 info 文件（安装树 5 实物） |
| 上游测试 | `TESTS = t_num checkopt checkoptcc`，**78 断言**（四口径取最大，静态 == 运行时）→ **76 PASS / 2 FAIL**，每 TEST rc：`t_num=0 checkopt=2 checkoptcc=0` |
| 消费者测试 | `test_package` **15 断言**全过（含鸿蒙特有 1 条） |

## 源改道四路 sha 证据（上游站已死）

上游主页 `http://nis-www.lanl.gov/~jt/Software/opt/` 于 **2011-04-28 消亡**（Debian
`copyright` 原文 "vanished upstream as of 2011-04-28"）。按任务卡口径取源以 Debian
pool 为准，并做四源交叉验证（curl 与 urllib 双栈，共 8 次取数）：

| # | URL | PF7 `_pf7_classify` | sha256 |
|---|-----|--------------------|--------|
| 1 | `https://ftp.debian.org/debian/pool/main/o/opt/opt_3.19.orig.tar.gz` | None | `9feb44c0…5acc` |
| 2 | `https://archive.ubuntu.com/ubuntu/pool/universe/o/opt/opt_3.19.orig.tar.gz` | None | `9feb44c0…5acc` |
| 3 | `https://mirrors.ustc.edu.cn/debian/pool/main/o/opt/opt_3.19.orig.tar.gz` | None | `9feb44c0…5acc` |
| 4 | `https://mirrors.tuna.tsinghua.edu.cn/ubuntu/pool/universe/o/opt/opt_3.19.orig.tar.gz` | None | `9feb44c0…5acc` |

**四路 distinct = 1**；`Content-Encoding` 实测 `None`（无 gzip 透明解码失配）。
双 `.dsc`（Debian `opt_3.19-4.dsc` 与 Ubuntu 同名文件）的 `Checksums-Sha256` 独立
佐证同值。**PF7 双坑实测**：`http://deb.debian.org/...` → 「明文 http 源」拦，
`https://deb.debian.org/...` → 「Debian 下游重打包源」拦，故 conandata 选
ftp.debian.org（classify=None）。取数与复现命令：`$TASK_DIR/w0/w0-1-version.md`。

tarball 内证：`configure.in` `AM_INIT_AUTOMAKE(opt,3.19)`、`version.texi`
`@set VERSION 3.19`、`NEWS` `=== 3.19 ==`。

## configure 随包依据（勿 autoreconf）

`configure` 头部 `Generated automatically using autoconf version 2.13`；tarball 自带
`configure/configure.in/aclocal.m4/Makefile.in/install-sh/missing`，
**无 `config.sub`/`config.guess`**（`configure.in` 无 `AC_CANONICAL_HOST/TARGET`，
不踩 config.sub/guess 陈旧族先例）。实测四个 autoconf 2.13 专属坑：

1. **命令行 `CFLAGS=...` 不被接受** → `configure: warning: CFLAGS=…: invalid host type`
   → `can only configure for one host and one target at a time`，rc=1。
   正解：标志走**环境前缀**（`CC=… CFLAGS=… ./configure`）+ **make 行**双钉。
2. **`configure.in` 末尾字面 `CXX=g++` + `AC_SUBST(CXX)`** 把 `CXX = g++` 固化进全部
   Makefile（设备与 CI 均无 g++）→ configure 期传 `CXX=clang++` 只能保证
   `AC_PROG_CXX` 探测通过，**make 行必须再覆盖一次** `CXX=clang++`。
3. **`--datarootdir=` 是 invalid option**（2.60 才引入）→ 不用
   `Autotools.configure()`，configure 调用由配方自持。
4. automake **1.4-p5** 的 install 规则带 `$(DESTDIR)` → `--prefix=/` +
   `make install DESTDIR=<package_folder>` 可用（实测 5 文件，`/` 无污染）。

## 硬依赖（静态 + 动态双 profile）

- 静态：`configure.in` 全部 `AC_CHECK_LIB` 只有 readline/termcap 两处且都在
  `--with-readline` 分支内（默认不传即关）；`AC_CHECK_FUNCS(strdup/snprintf/longjmp)`
  全 libc 内建；Debian `.dsc` `Build-Depends: debhelper-compat, texinfo, debhelper`
  （打包侧工具，非本配方依赖）；Conan `requires = ()`。
- 动态：`readelf -d` 三个测试程序 NEEDED 仅 `libc.so`（`testcc` 另需设备自带
  `libc++_shared.so`）；`nm -u libopt.a` 140 个未定义符号全为 libc + 归档内部
  `ag_*`。**libcheck 未被使用**（测试是 shell + 裸 C）；无 lpk 类前置任务。
- 工具缺口替代：`g++` 缺 → 显式 `clang++`（make 行）；`makeinfo` 缺 → 上游预生成
  `opt.info*` mtime ≥ `opt.texi`，`make install` 不调 makeinfo；`ldd` 缺 → `readelf`。

## 问题与解决

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `test/testcc.cc: fatal error: 'iostream.h' file not found` | 前标准 C++ 头，libc++ 无此文件 | 补丁 `0001`：`#include <iostream>` + `using namespace std;`（与 Debian `opt_3.19-4` 的 `debian/patches/test.patch` 逐字同源） |
| 2 | `g++: No such file or directory`（`opt_regcc.o`/`testcc.o`） | `configure.in` 字面 `CXX=g++` 经 AC_SUBST 固化 | make 行 `CXX=clang++` 覆盖 + configure 期显式 CC/CXX |
| 3 | 编译标志不可信 | autoconf 2.13 不认命令行 `VAR=value`；CI worker 泄漏 CFLAGS | 环境注入 + make 行双钉 `-O3 -pipe -DNDEBUG [-fPIC]` |
| 4 | `ln: cannot create hard link … Operation not permitted`（`optcc.cc: opt.c` 规则） | HMDFS 不支持硬链接 | build() 内把 src/Makefile 该行 `ln -f`→`cp -f`（先例 #8，免 refresh_patch），并**真的执行一次**该规则留正面证据（日志行 `[HMDFS] hardlink rule fix: hit=1 residual=0`） |
| 5 | `checkopt` 2 条断言必失败 | 见下节「上游已知测试缺陷」 | 白名单闸放行且只放行这两条；不改测试、不改库 |
| 6 | configure rc=0 但产物可能没落盘 | HMDFS config.status 族假绿（先例 #9） | configure 后清点 5 个 `AC_OUTPUT` 产物；install 后清点 5 个安装实物，缺即抛错 |

## 上游已知测试缺陷（不凑绿，白名单闸）

失败的两条（`checkopt` 56 断言中的 2 条）：

- `checkit USHORT error`：`testtypes -n -1 2>/dev/null | grep 65535`；
- `checkit ULONG error`：`testtypes -o -1 2>/dev/null | grep 4294967295`。

根因链（一手证据）：

1. `opt_atou()` 实现是 `x = (unsigned long)atof(s)`，`atof("-1") = -1.0`，**浮点 →
   无符号整型转换是 C 未定义行为**；
2. aarch64 的 `fcvtzu` 走**饱和语义 → 0**（x86-64 才会回绕成 18446744073709551615），
   实测 `testtypes -n -1` 打印 `n=0`、`-o -1` 打印 `o=0`，与 `will use [0]` 警告一致；
3. 期望值 `4294967295 = 2^32-1` 是 **32 位字长写死**，本机 `unsigned long` 为 64 位，
   任何 64 位平台都不可能打印出它。

**第三方佐证**：Debian `opt_3.19-4.debian.tar.xz` 的 `debian/rules` 原文：

```make
# FIXME: Hiding eyes from test failure here.
#        This is not worse than before where the test was not even run
override_dh_auto_test:
	dh_auto_test || true
```

即官方打包对**同一组失败**选择容忍而非修改断言；其 `test.patch` 与本任务补丁 0001 同源。

**处置**：`build()` 里逐 TEST 单跑留档 rc → 再跑 `make check` 取框架视角 → 两阶段
互核 → 失败集合**必须 ⊆ {USHORT error, ULONG error}**，出现任何其它失败、缺 TEST、
或两阶段判读不一致即抛错阻断；结果以 `HMBS_UPSTREAM_TEST_RESULT` 如实上报
（`failed=2`），**不写全绿**。改断言 = 凑绿（禁止），改库也救不回 32 位期望值。

## 78 断言取数命令（四口径取最大，静态 == 运行时）

```sh
SRC=<解包目录>
# ① 源码宏数（静态）
grep -cE '^[[:space:]]*checkit(neg)? [^()]' "$SRC/test/checkopt"     # 56
grep -cE '^[[:space:]]*checkit(neg)? [^()]' "$SRC/test/checkoptcc"   # 10
grep -cE '^\{"' "$SRC/test/t_num.c"                                  # 12
# ② 框架注册数
grep -E '^TESTS' "$SRC/test/Makefile.am"                             # 3（用例数，非断言数）
# ③ 运行时 assertion 数（剔除内嵌 make 噪声行）
cd <build>/test
'../test/checkopt'   > r1.log 2>&1; echo "rc=$?"                     # rc=2
sed '/^make:/d' r1.log | tr -cd '.' | wc -c                          # 54（通过）
sed '/^make:/d' r1.log | grep -c '^Error:'                           # 2（失败）→ 56
'../test/checkoptcc' > r2.log 2>&1; echo "rc=$?"                     # rc=0；点 10 → 10
./t_num > r3.log 2>&1; echo "rc=$?"; grep -c CORRECT r3.log          # rc=0；12
# ④ 消费者断言数（test_package，独立分栏不并入 N）
grep -cE '^[[:space:]]*CHECK\(' test_package/test.c                   # 15
```

合计 **78 = 56 + 10 + 12**（≥ 75，任务卡达标）；四口径最大候选 = 78，无差额需归因。

## 验证结果（设备实测）

```text
configure rc=0，AC_OUTPUT 5 件产物齐（Makefile src/Makefile test/Makefile ext/Makefile opt.spec）
make -j1 rc=0（8 个 libopt 对象 + 12 个测试程序）
make check：PASS t_num / FAIL checkopt（2 条已知）/ PASS checkoptcc → 1 of 3 failed（白名单内）
make install DESTDIR → 5 实物，/ 无污染
test_package：all 15 assertions passed
```

## 已知限制 / 遗留风险

- `checkopt` 恒 `rc=2`（上述两条上游缺陷），配方以白名单闸放行并如实上报 `failed=2`；
  上游若日后修掉这两条，白名单是超集，不会误伤。
- `readline` 增强未启用（设备无 libreadline/libtermcap）；如需启用须先出前置任务。
- `src/Makefile` 的 `optcc.cc` 规则虽已改写并正面执行过一次，但它不挂在
  `all/check/install` 主路径（本版 automake 的 `all-am` 不依赖 `BUILT_SOURCES`），
  属防御性修复。
