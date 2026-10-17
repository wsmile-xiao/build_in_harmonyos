# combine 0.4.0 适配笔记

## 编译环境

- 构建系统：autotools（autoconf 2.69 生成的 `configure` 随 tarball 发布，无需 autoreconf）
- 编译日期：2026-09-26
- 目标：HarmonyOS PC（`uname -s` = HarmonyOS，`uname -m` = aarch64；OpenHarmony 包仓 profile `os=OHOS arch=armv8 compiler=clang compiler.version=15`）
- 编译器：clang 15.0.4（`/data/service/hnp/bin/clang`，由 conan profile 的 `tools.build:compiler_executables` 提供）
- 构建主机：A 机，`CONAN_HOME=$HOME/tmp/ch/home-z68-combine`，Conan 2.29.1
- 状态：**built**（本地 `conan create` 通过，上游 `make check` 真跑）

## 编译步骤（配方实际执行的路径）

```sh
# source/：解官方包 + 补可执行位（E490）
# build/：4 条补丁 -p1 应用 → 树内 configure
env -u CONFIG_SHELL SHELL=/bin/sh sh configure --prefix=/ \
  '--bindir=${prefix}/bin' '--sbindir=${prefix}/bin' '--libdir=${prefix}/lib' \
  '--includedir=${prefix}/include' '--oldincludedir=${prefix}/include' \
  --disable-nls ac_cv_lib_guile_gh_scm2bool=no ac_cv_header_libguile_h=no
env -u CONFIG_SHELL SHELL=/bin/sh make -j1
env -u CONFIG_SHELL SHELL=/bin/sh make -j1 check          # ★ 上游测试真跑
#   check 跑完 → 配方把 doc/combine.info 按 build_folder 里的原件快照写回，
#   并用一手算出的 size+sha256 逐字节断言（问题 5 / W68R-COMB-01）
env -u CONFIG_SHELL SHELL=/bin/sh make install DESTDIR=<package_folder> guiledatedir=/share/combine_scm
```

## 依赖判定（W0）

`ci/scripts/preflight_check.sh combine/0.4.0` → `[OK] 预检通过（无依赖需要检查）`。

**本包零 Conan 依赖**，两条候选依赖都不是必须的：

1. **guile = 可选依赖，OHOS 不部署。**
   `configure.ac:26` 只有 `AC_CHECK_LIB([guile],[gh_scm2bool])`，
   `AC_CHECK_HEADERS` 探 `libguile.h`；**没有任何 `AC_MSG_ERROR`/required 判定**。
   全部 guile 代码都在条件编译之内：`src/df_common.h:31,34,36,37,202` 与
   `src/main.c:21` 用 `HAVE_LIBGUILE`/`HAVE_LIBGUILE_H` 包起来，唯一 guile 翻译单元
   是 `src/iguile.c`。⇒ 缺 guile 时只是不定义这两个宏，构建照常。
   ⛔ 不为了"凑依赖"去 `requires("guile/...")`（guile 尚未 release，会撞 R36），
   ⛔ 不造 dummy 包/假头。
   配方还把 `ac_cv_lib_guile_gh_scm2bool=no` / `ac_cv_header_libguile_h=no` **显式钉死**：
   构建主机上可能残留 `/usr/local/include/libguile.h`（guile 在别的窗口正在适配），
   一旦 `ac_cv_header_libguile_h=yes` 就会打开 `HAVE_LIBGUILE` 分支并触发 `GUILE_FLAGS`
   宏（`configure:12152` 跑 `$GUILE_CONFIG info pkgdatadir`，worker 上没有 `guile-config`
   就直接失败），同时改变 `GUILE_SITE` ⇒ 构建结果随机器残留漂移。钉死后行为可复现。
2. **gettext/libintl = 关掉。** `po/` + `intl/` 走 `AM_GNU_GETTEXT`（非 external），
   目标上没有 libintl 运行时，消息目录也不是交付物 ⇒ `--disable-nls`。
   实测 `configure` 的 `ac_config_files` 会生成 `intl/Makefile` 与 `po/Makefile.in`；
   `USE_NLS=no` 之后 `po/Makefile.in.in` 的 `all: check-macro-version all-@USE_NLS@`
   退化成 `all-no:`（空目标）、`install-data-no: all` ⇒
   **worker 上没有 `msgfmt`/`autopoint`（实测二者只在 `~/.harmonybrew/bin` 存在）也能构建**。

## 遇到的问题与解决方案

| # | 症状（第一条真实错误原文） | 根因 | 最小复现 | 解决方案 |
|---|---|---|---|---|
| 1 | `configure: error: working directory cannot be determined`（前面 26 行 `shell-init: error retrieving current directory: getcwd: cannot access parent directories`） | profile `ci/conan/profiles/ohos-aarch64` 的 `[buildenv]` 导出 `CONFIG_SHELL=/data/service/hnp/bin/bash`；autoconf 会用 `$CONFIG_SHELL` 重新 exec 自己，而 hnp bash 在 HMDFS 支撑的 conan 构建目录里 `getcwd()` 必挂（E386 同族） | `conan create` 走到 `RUN: ".../configure" --prefix=/ ...` 即挂；同一目录 `env -u CONFIG_SHELL SHELL=/bin/sh sh configure ...` 立即通过 | 弃用 `Autotools.configure()`，沿用仓内 `gnu-pw-mgr/2.7.4`、`gtypist/2.10.1` 已合入形状：`SH = "env -u CONFIG_SHELL SHELL=/bin/sh"` 前缀 + 树内手工 configure/make，并自带 conan 默认的那套 `--prefix=/ --bindir=... --libdir=...` 参数（⛔ 用 `--build/--host` 绕，会被判交叉编译、`AC_RUN_IFELSE` 静默跳过） |
| 2 | `./config.status[826]: can't create ./confFUdHCP/subs1.awk: Permission denied` ⇒ `config.status: error: could not setup config files machinery` | autoconf 2.69 写进 `config.status` 的临时目录逻辑用 `umask 077` 建 `./confXXXXXX`；HMDFS 上该目录落成 `drwx--S---`，随后写入被拒（E011/E114 族） | **同一构建目录、同一 `/bin/sh` 的 A/B**：`umask 077` → `ls -ld` = `drwx--S---`、`echo x > $d/t` → `Permission denied`；`umask 002` → `drwxrws--x`、写入 OK。另测 `(umask 077 && mkdir $t)` 的 fallback 分支落成 `drwxrws--x`、写入 OK ⇒ **只有 `mktemp -d` 这条分支炸** | `patches/0003-configure-umask.patch`：两处 `umask 077` → `umask 002`。选 `002` 而不是像 gtypist 那样直接删掉 `umask 077 &&`：删掉后目录模式取决于环境 umask，不确定；`002` 是确定值且保留"组内可读"语义 |
| 3 | `configure: error: cannot guess build type; you must specify one`（`config.guess` timestamp=`2004-03-12`，`uname -s`=HarmonyOS 不识别） | E160/E007 一族（仓内 B 先例编号 M4）。**本快照的 `config.guess` 分支体是 `echo <triplet>; exit 0 ;;` 风格**，`grep -c 'GUESS=' config.guess` = **0** ⇒ 仓内 `scripts/patch-autotools-ohos.pl` 产出的 `GUESS=${MACHINE}-unknown-linux-ohos` 形态在本快照里根本不会被读到（helper 的形态只在 2021 重构之后有效） | 见下"最小复现（补丁级）"：给 `config.guess` 喂一个 `uname -s` = HarmonyOS 的 shim，未打补丁时打印 `unable to guess system type` 并 exit 1，打补丁后输出 `aarch64-unknown-linux-ohos` | 按**本快照自己的风格**生成成对补丁 `0001-config.guess.patch`（`echo ${UNAME_MACHINE}-unknown-linux-ohos; exit 0 ;;`）+ `0002-config.sub.patch`（4 处白名单）。⛔ 直接拿别包补丁的锚点（本项目实证过 Hunk FAILED）。补丁摘掉了 helper 的 `__OHOS__` LIBC 探测 hunk，且 `grep -n "^+.*__OHOS__" patches/*.patch` 空 ⇒ PF5 合规 |
| 4 | `make check` 起手 `sh: test_combine: No such file or directory`（ENOENT，指向解释器不是脚本） | 上游 `tests/test_combine` 首行 `#!/bin/bash`，**HarmonyOS 上没有 `/bin/bash`**（`ls /bin/bash` → No such file；`/bin/sh` → `/system/bin/sh`；`bash` 只在 `~/.harmonybrew/bin/bash`，CI worker 不保证有） | `ls /bin/bash`；`/bin/sh -c '[[ "" == "" ]] && echo OK'` → `OK`（证明脚本体的 bashism 目标 sh 吃得下） | `patches/0004-test-combine-shebang.patch`：只把 shebang 改成 `#!/bin/sh`，**不动脚本体**（实测 `[[ ]]`/`==` 在 `/system/bin/sh` 下可用，无需 POSIX 化） |
| 5 | 首轮实做的症状：`make: *** No rule to make target ... makeinfo` 没出现，但**交付包里的 `share/info/combine.info` 是 0 字节**（tarball 同路径 97620 B、sha256 `90751f24deba1406…`；构建树 `doc/combine.info` 同态 0 B、mtime 即那轮构建时刻 18:25） | `doc/Makefile.am` 只有 `info_TEXINFOS = combine.texinfo`，`all-am` 与 `check-am` 都依赖 `$(INFO_DEPS) = combine.info`，目标上没有 makeinfo（`command -v makeinfo` = NONE）。**压时间戳不足以让 `.texinfo.info` 规则不触发**：`make` 阶段 doc/ 先印 `Updating ./version.texi`（依赖链 `combine.info ← version.texi ← stamp-vti ← combine.texinfo+configure`），再生件比 `combine.info` 新 ⇒ `make check` 的 `Making check in doc` 照样执行该规则；`missing --run makeinfo -o combine.info combine.texinfo` 起手就把 `$@` 截成 0，而同一规则里的备份守卫 `missing --run makeinfo --version` 为假 ⇒ `restore` 保持 `:`、原件没被移进 `.am$$` ⇒ 截断不可逆，随后 `make install` 把空件装进包 | 读 `doc/Makefile.in` 的 `.texinfo.info` 规则体（备份/执行/还原三段）；对照首轮 create 日志同段既印 `Updating ./version.texi` 又印 `missing[63]: makeinfo: inaccessible or not found`（整改后复跑仍如此：本轮 `reports/w3-local-ci.log:3222` 与 `:3281`） | 三段式护栏（配方 `build()`/`package()` 里的 `_info_snapshot` / `_info_verify` / `_info_check_packaged`）：①任何 make 之前把原件字节快照到 `self.build_folder`（⛔ 留在源码树），参照 = **解包后一手算出的 size + sha256**（⛔ 拿 97620 这类常数当唯一判据），原件到手即 0 字节则拒绝立参照；②`make -j1 check` 跑完后若 size/sha 与快照不符（含截成 0）就**按快照原样写回**；③写回后逐字节断言等于参照，不等即 `ConanException`（⛔ 只打 warning 放行），并打印机器可读判决行 `COMBINE_INFO_INTEGRITY=pre=<size> post=<size> sha=<sha256 前 12 位> restored=<bool>`；④`make install` 之后再断一次包内 `share/info/combine.info`。压时间戳仍保留，但**降级为"少跑一次规则"的优化**，不再当交付依据。**⛔ 把 MAKEINFO 占位成 `:`/`true`**：那条规则会先把 `$@` 备份进 `.am$$`、让假 makeinfo "成功"、最后 `rm -rf $$backupdir`，真 info 件会被吃掉；**⛔ 从 `package()` 里悄悄不装 info 文件**（那等于改变上游安装面且不披露） |
| 6 | 潜在：`src/combine_scm` 的安装目录退化成包根散目录 | `guiledatedir = @GUILE_SITE@/combine_scm`，本构建不启 guile ⇒ `GUILE_SITE` 为空（`configure:12152` 那条赋值在 `GUILE_FLAGS` 分支里，不执行）⇒ 目录变成 `/combine_scm`；`DESTDIR` 兜住后产物落在 `<package_folder>/combine_scm` | `grep -n "GUILE_SITE=" configure` 只命中 1 处（在 guile 分支内） | `package()` 用 make 命令行变量覆盖：`guiledatedir=/share/combine_scm` ⇒ 上游两个 `.scm` 载荷落到 `share/combine_scm/`。⛔ 改生成的 `Makefile.in`（R6） |

## 最小复现（补丁级，可重跑）

设备侧脚本 `$HOME/tmp/uc2/z68-combine-fix/w-1.sh`（本窗生成的证据脚本），流程：
从 pristine 快照取 `config.guess`/`config.sub`/`tests/test_combine` → `-p1` 打 4 条补丁
→ 造一个 `uname` shim（`-s`→HarmonyOS、`-m`→aarch64）→ 跑 `sh config.guess`
→ 用产出的 triple 跑 `sh config.sub`。实测输出：

```
shim uname -s => HarmonyOS
config.guess -> aarch64-unknown-linux-ohos            CG_OK
config.sub aarch64-unknown-linux-ohos -> aarch64-unknown-linux-ohos   CS_OK
config.sub aarch64                -> aarch64-unknown
config.sub aarch64-unknown-linux-gnu -> aarch64-unknown-linux-gnu     （未回归）
PF5 OK   （patches/*.patch 的新增行里没有 __OHOS__）
ALL_VERIFY_PASS
```

`config.sub` 需要 **4 处**同时补，少一处就会错：
`maybe_os` 白名单（不补则 `linux-ohos` 不被当 KERNEL-OS 组合）、
无厂商 CPU 表（`aarch64`）、有厂商 CPU 表（`aarch64-*`）、
以及 OS 直通表 —— 最后这处是关键：2004 版 config.sub 有
`-linux*)  os=$(echo $os | sed 's|linux|linux-gnu|')`，
不把 `-linux-ohos*` 加进前面的直通表，`-linux-ohos` 会被改写成
`-linux-gnu-ohos` 这种畸形 triple（**不报错、静默错**）。

## 已试过的失败方案（⛔ 别重复踩）

1. **`Autotools(self).configure()` 标准路线** —— 直接死在
   `configure: error: working directory cannot be determined`（问题 1）。
   `Autotools` 会 profile 注入的 `CONFIG_SHELL=hnp bash` 原样带进 configure。
2. **`--build/--host=aarch64-unknown-linux-gnu` 绕过 config.guess**
   （`archives/a/a52dec/0.7.4` 与 `gnu-pw-mgr/2.7.4` 里有这个形状）——
   **本包不采纳**：那是把原生构建伪装成交叉编译，`AC_RUN_IFELSE` 类探测
   （`AC_FUNC_MALLOC`/`AC_FUNC_MMAP`/`AC_FUNC_MBRTOWC`/`AM_C_PROTOTYPES` 的
   `c_ansi` 判定）会全部走 cross-compiling 分支静默跳过；
   autotools-patterns.md #0 与本项目规则都把 `--build/--host` 列为禁用。
   ⇒ 走 config.guess/config.sub 补丁路线，原生构建，探测真实执行。
3. **`MAKEINFO=true` 占位**（gtypist 对 help2man/makeinfo 的做法）——
   在本包的 `doc/` 上会把 tarball 自带的真 `combine.info` 吃掉（问题 5）。
4. **只压 `doc/combine.info` 的时间戳**（首轮实做就栽在这里；独立 W4 判决
   `W68R-COMB-01` 证伪）——`make` 阶段会再生 `version.texi`，`make check` 时
   `.texinfo.info` 规则照样执行，缺失的 makeinfo 用 `-o` 把 97620 B 的原件截成
   0 字节，而备份守卫为假（`restore=:`）⇒ 原件回不来，空件被装进包。
   ⇒ 现方案是「每次 make 前快照原件字节 + 全部 make 跑完按快照写回 + 用一手算出的
   size/sha256 逐字节断言」（问题 5），时间戳只留作减少一次无谓触发的优化。
5. **直接复用 `scripts/patch-autotools-ohos.pl` 的产物** ——
   helper 的 HarmonyOS 分支写 `GUESS=${MACHINE}-unknown-linux-ohos`，
   而本快照 `grep -c 'GUESS='` = 0（2004-03-12 早于该重构）⇒ 打了也不会生效。
   helper 的 `__ANDROID__`→`__OHOS__` LIBC hunk 在本快照里也锚不到
   （`grep __ANDROID__ config.guess` 无命中），而且 PF5 禁止补丁新增行出现 `__OHOS__`。
6. **把 `test_combine` POSIX 化**（`[[ x ]]` → `[ x ]`、`==` → `=`）——
   实测目标 `/bin/sh` 接受 `[[ ]]`/`==`，没必要动脚本体；改 shebang 一处即可，
   面更小、更可审。

## 上游测试清点与五维台账（R51）

**静态清点证据**（不是"日志反填"）：

- `tests/Makefile.am` 内容只有 `EXTRA_DIST=...` 加一个**手写目标**：
  ```
  check:
      $(srcdir)/test_combine $(srcdir) $(top_builddir)/tests
  ```
  ⇒ 没有 `TESTS` 变量、没有 `check_PROGRAMS`、没有 dejagnu/ctest 注册入口。
  注册面 = 1 个 `make check` 目标，脚本内展开为 **7 个用例**。
- `tests/Makefile.in` 复刻该目标于 432-433 行（319-320 行是 automake 内建的
  `check: check-am`）；黄金件 `result1.txt result2.txt result4.txt result5a.txt
  result5b.txt result6.txt result7.txt` + `stats1..7.txt`；输入件 `test.1..test.6`。
- `tests/test_combine`（3326 B）内 7 段 `Test N: (...) PASSED/FAILED`，
  每段 1 次 combine 调用 + **若干次 `diff -q` 黄金比对**：
  Test 1/2/3/4/6/7 各 2 次，**Test 5 是 3 次**（双输出文件 `result5a` + `result5b`）
  ⇒ 静态共 **15 次比对**。
- 顶层 `Makefile.am`：`SUBDIRS = lib intl src doc tests po m4` ⇒ `make check`
  会递归到 tests；`src/` 是 `bin_PROGRAMS = combine`，`lib/` 是 `noinst_LIBRARIES = libdf.a`。

| 维度 | 数 | 依据 |
|---|---|---|
| `N_static`（上游静态声明用例） | **7** | `tests/test_combine` 内 7 个 `Test N:` |
| `N_registered`（构建系统注册的可执行入口） | **7** | 1 个手写 `check:` 目标，展开 7 个用例，无条件编译剔除 |
| `N_executed`（适配后实际执行） | **7** | `build()` 里 `make -j1 check` 真跑，日志逐条出现 `Test 1..7` |
| 跳过 / 未执行 | **0** | 无一条被 skip |
| 失败 | **1** | Test 7，原因见下 |
| 黄金比对次数 | **15** | 静态 15 次 `diff -q`（计数入口：`tests/test_combine` 的 11 行 15 次调用，行号 15/23/31/39/47/48/49/57/58/66/67；Test 1-4/6/7 各 2 次、Test 5 三次）；**实执行 14** —— 用例判定是 `[[ 比对A ]] && [[ 比对B ]]` 短路形，Test 7 的第一个比对不匹配后第二个不执行 ⇒ 14 次里 **13 匹配 / 1 不匹配**（那 1 次不匹配就是 Test 7 的 `stats.txt` vs `stats7.txt`） |
| `N_consumer`（新增消费者测试程序） | **1** | `test_package/test.sh`（按脚本的 **7 个编号节**计 `N_assertion=7`；第 7 节内含 2 项反向检查 7a/7b ⇒ 检查项共 8，断言口径仍按 7 节计） |

**`make check` 实测判决原文**（本轮 A 机 `reports/w3-local-ci.log:3292-3298`，`conan create` 日志逐用例）：

```
Test 1: (General matching, reference-based output.) PASSED
Test 2: (General matching, data-based output.) PASSED
Test 3: (Only necessary ref checking.) PASSED
Test 4: (Constant strings and reference filler.) PASSED
Test 5: (Multiple reference matches.) PASSED
Test 6: (Delimited reference fields and sums.) PASSED
Test 7: (Extension load and field modification.) FAILED
```

⇒ 上游通过率 **6/7**（分母保持 7，⛔ 不删用例、⛔ 不缩分母、⛔ 不把 FAILED 写成 skipped）。

**Test 7 的确定技术原因**：该用例是
`combine -X '../src/util.scm' -w -D , -d , -o '1(rpad input-field 5),2(lpad input-field 10)' test.5`
—— `-X` 是 **guile 扩展加载**（`--extension-init-file`）。OHOS 侧不部署可选依赖 guile
（见"依赖判定"），所以 scheme 的 `rpad`/`lpad` 字段函数不存在、输出与
`result7.txt`/`stats7.txt` 不匹配。这不是 OHOS 移植缺陷，而是**可选依赖未启用**的必然后果；
`--disable-nls` 对 tests 的可见性没有影响（tests 里没有任何 NLS/locale 相关用例，
`LANG`/`LC_*` 不参与黄金件比对，Test 1-6 全绿即为证）。

**上游测试脚本的一条假阳性风险（如实披露）**：`test_combine` 用
`[[ "$( diff -q A B )" == "" ]]` 判等。实测目标上的 `diff -q` 语义正常
（同文件 → stdout 空；异文件 → `Files x1 and x3 differ`），
**但传入不存在的文件时 stdout 也是空的**（报错只进 stderr）⇒ 若某个用例的输出文件
根本没生成，上游脚本会**误判 PASSED**。另外该脚本最后一条命令是 `rm`，
**整脚本退出码恒为 0**，所以 `make check` 返回 0 并不代表 7/7。
本包因此把判决建立在"逐用例点收日志 + `test_package` 独立逐字节断言"两件事上，
不依赖 `make check` 的退出码。

## 上游测试用例统计

按 `templates/积分赛事PR模板.md` 的表形给出（与 PR 正文同源；数量列一律纯整数）：

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游无 `TESTS` / `check_PROGRAMS` / ctest / dejagnu 注册入口 |
| 集成测试 | 7 | 来源：`tests/Makefile.am` 的手写 `check:` 目标 → `tests/test_combine` 内 7 个端到端 CLI 用例（共 15 次 `diff -q` 黄金比对） |
| 其他测试 | 0 | |
| **合计** | **7** | |

## 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | |
| 集成测试 | 7 | 不变 | 上游 7 个用例在 `build()` 内 `make -j1 check` 全部真实执行：6 通过 / 1 失败（Test 7 = guile `-X` 扩展用例，可选依赖未启用），分母保持 7 |
| 消费者测试（test_package） | 1 | 新增 | `test_package/test.sh`，以使用者身份真实运行包内 `combine` 二进制，退出码 + 输出双判据按脚本的 **7 个编号节**计（`N_consumer` = 1，`N_assertion` = 7；第 7 节含 2 项反向检查 7a/7b，故检查项 8） |
| **合计** | **8** | +1 | |

### 上游 7 个用例逐条判决（`make check` 实测原文见上一节）

| # | 用例 | 黄金件 | 结果 |
|---|---|---|---|
| 1 | General matching, reference-based output | stats1 + result1 | PASSED |
| 2 | General matching, data-based output | stats2 + result2 | PASSED |
| 3 | Only necessary ref checking | stats3 + result2 | PASSED |
| 4 | Constant strings and reference filler | stats4 + result4 | PASSED |
| 5 | Multiple reference matches | stats5 + result5a + result5b | PASSED |
| 6 | Delimited reference fields and sums | stats6 + result6 | PASSED |
| 7 | Extension load and field modification（guile `-X`） | stats7 + result7 | FAILED（可选依赖 guile 未启用） |
| **合计** | **7** | 15 次 `diff -q` 比对 | 6 通过 / 1 失败 / 0 跳过 |

## 源码修改（4 条补丁，全部 `-p1`，`apply_conandata_patches` 应用）

| 文件 | 改了什么 | 为什么 |
|---|---|---|
| `patches/0001-config.guess.patch` | 在 `case "${UNAME_MACHINE}:..."` 的第一个分支前插入 `*:HarmonyOS:*:*)`，体内 `echo ${UNAME_MACHINE}-unknown-linux-ohos; exit 0 ;;` | 问题 3；本快照是 echo/exit 风格，不能用 GUESS= 形态 |
| `patches/0002-config.sub.patch` | 4 处白名单：`maybe_os` 加 `linux-ohos*`；无厂商 CPU 表加 `aarch64`；有厂商 CPU 表加 `aarch64-*`；OS 直通表加 `-linux-ohos*` | 问题 3；漏第 4 处会静默产出 `-linux-gnu-ohos` 畸形 triple |
| `patches/0003-configure-umask.patch` | `configure`（生成文件，autoconf 写进 `config.status` 的那段）里两处 `umask 077` → `umask 002` | 问题 2；HMDFS 上 `mktemp -d` 在 umask 077 下建出不可写的 `drwx--S---` |
| `patches/0004-test-combine-shebang.patch` | `tests/test_combine` 首行 `#!/bin/bash` → `#!/bin/sh` | 问题 4；HarmonyOS 无 `/bin/bash` |

补丁由 `patches/` 生成器（本窗自写 `~/tmp/uc2/z68-combine-fix/genpatches.py`）
针对**本快照逐字锚定**生成：每条替换都断言"命中恰好 1 次"，锚不到就直接失败，
不做模糊匹配 ⇒ 不会产生"Hunk FAILED"或空补丁。

## 依赖版本

无 Conan 依赖（`requirements()` 为空）。
构建工具依赖（由 CI worker 环境提供，不在配方里声明）：`make`（GNU Make 4.4.1）、
`clang` 15、`perl`（`automake` 的 `missing` 包装器）、`/bin/sh`（toybox）。
不需要：`autoconf`/`automake`/`aclocal`（tarball 已带生成好的 `configure` 与 `Makefile.in`）、
`msgfmt`/`autopoint`（`--disable-nls`）、`makeinfo`（问题 5：不重生成 info，用 tarball 自带件 + 字节快照写回）、`yacc/bison`（`AC_PROG_YACC`
只探测，`src/` 里没有 `.y`）、`guile`（可选依赖，显式关）。

## 验证结果

```bash
# 1) conan create（W3/G2 输入，A 机）
conan create archives/c/combine/0.4.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
#   → RC=0；4 条补丁全部 "Apply patch (portability)" 成功，无 Hunk FAILED
#   → 上游 make check 逐用例 6 PASSED / 1 FAILED（Test 7）
#   → 消费者测试 7/7 passed

# 2) 包内产物
<package_folder>/bin/combine              113088 B  -rwxrwx---
<package_folder>/share/combine_scm/*.scm  （guile 扩展载荷，未链 guile 时装载器也不用它）
<package_folder>/share/info/combine.info    97620 B  -rw-rw----   ★与 tarball 原件逐字节同

# 3) 二进制真实执行
$ combine --version
combine (combine) 0.4.0            # RC=0
$ combine --help                   # RC=0，完整 usage

# 4) info 交付件完整性（W68R-COMB-01 整改后的产物级验收，19:21 那轮）
$ ls -l /storage/Users/currentUser/tmp/ch/home-z68-combine/p/b/combi0c2d56b740372/p/share/info/combine.info
-rw-rw---- 1 20001006 file_manager 97620 2026-09-26 19:21 .../combi0c2d56b740372/p/share/info/combine.info
$ sha256sum <package_folder>/share/info/combine.info
90751f24deba1406dc147e6e4392224749a2a74977c1fc596928f5ed9c9b3317
#   ≡ 一手从 tarball 解出的 combine-0.4.0/doc/combine.info（tar -xzOf + sha256sum，97620 B、同 sha256）
#   配方判决行 reports/w3-local-ci.log:3310 →
#     COMBINE_INFO_INTEGRITY=pre=0 post=97620 sha=90751f24deba restored=true
#   （pre=0 ⇒ 原件在本轮 make check 里确实又被截成 0；restored=true ⇒ 按快照写回并通过断言）
#   包内复核 reports/w3-local-ci.log:3483 →
#     COMBINE_INFO_PACKAGED=size=97620 sha=90751f24deba expected=97620/90751f24deba
#   同段仍印规则触发证据：:3222 `Updating ./version.texi`、:3281 `missing[63]: makeinfo: inaccessible or not found`
#   ⇒ 时间戳压制没有让规则不触发；交付面靠的是快照/写回/断言，不是 utime
```

- 编译状态：通过（`conan create` RC=0）
- 上游测试用例通过率：6/7（Test 7 因可选依赖 guile 未启用而失败，分母保持 7）
- 新增测试用例通过率：7/7（`test_package/test.sh` 的 7 个编号节断言，第 7 节含 2 项反向检查）
- info 交付件：`share/info/combine.info` = **97620 B / sha256 `90751f24deba1406…`**，与 tarball 原件逐字节相同（整改前该件在包里是 0 字节）

**本轮（19:13–19:21 复跑，A 机）的证据锚**：

- `conan-verify` → `G0/G1/G2/G3/G4` 全 PASS（`reports/conan-verify-report.md`，判决只认 `## G2:` 节行）
- W3 本地 CI `reports/w3-local-ci.log` sha256 =
  `bc32f6424ab10c1a55a37068874352aa8e52d47fd655525029f2e55bfe7e0616`
  ；构建期运行时件 `.ci-result.json` 当时抄录的 `log_sha256` 与之同值（该件被仓根 `.gitignore` 的 `reports/` 规则排除、不入库 ⇒ 此处只作留痕，⛔ 当可回读的互锁载体）；`exit_code=0`、`integrity_hash=7ec8750d46a3cbdc`；
  `[step]` 47 条、`_RESULT=` 8 条（旧锚 `1333df0b0f61…`/48 条随本轮失效，属预期）
- 本轮 `Package folder` = `/storage/Users/currentUser/tmp/ch/home-z68-combine/p/b/combi0c2d56b740372/p`
  （⛔ 拿 `conan cache path` 不带 rrev 去解析 —— 会落到旧修订、造出假 not-found）
- 五维台账最终值：`N_static=7` / `N_registered=7` / `N_executed=7` / 跳过 0 / 失败 1（Test 7）/
  `N_consumer=1` / `N_assertion=7`（7 个编号节，检查项 8）；黄金比对静态 15、实执行 14、匹配 13、不匹配 1
- `reports/` 被仓根 `.gitignore` 排除、不随 PR 入库 ⇒ 对外核验以本文件的实算 sha256 为锚

## 交付物

| 文件 | 说明 |
|------|------|
| `conanfile.py` | 配方（`package_type = application`，零依赖，`env -u CONFIG_SHELL SHELL=/bin/sh` 路由，含 `doc/combine.info` 的快照/写回/逐字节断言三 helper） |
| `conandata.yml` | 官方源 URL + 实算 sha256 + 4 条补丁清单 |
| `patches/0001..0004` | 见上表 |
| `test_package/conanfile.py` | `VirtualRunEnv` + `tested_reference_str`，`test()` 真实执行 `test.sh` |
| `test_package/test.sh` | 消费者行为测试源文件，7 个编号节的退出码+输出双判据（第 7 节含 2 项反向检查） |
| `test_package/MANIFEST.yml` | 上游 7 用例逐条声明 + 五维台账 + 消费者 7 节断言口径 |
| `manifest.yaml`（版本级）/ `archives/c/combine/manifest.yaml`（软件级）/ `README.md` / `commands.json` | 元数据与 R38 命令声明 |
| `notes.md` | 本文件 |

## 注意事项 / 适用边界

1. 本笔记的 4 条补丁只对 **combine 0.4.0 的 2004-03-12 autotools 快照**逐字锚定；
   换版本必须重新生成（⛔ 拿别包/别版本的锚点）。
2. `config.guess` 的 HarmonyOS 分支产出 `${UNAME_MACHINE}-unknown-linux-ohos`，
   在 aarch64 真机上就是 `aarch64-unknown-linux-ohos`；`config.sub` 的 4 处白名单
   只补了 `aarch64` 与 `linux-ohos` ⇒ **若换成 x86_64 目标需另加 CPU 项**（本机没有该形态，
   未测不猜）。
3. 关掉 guile 的代价明确写在这里：**Test 7 永远失败**，且 `-x/--extension`、
   `-X/--extension-init-file` 两条 CLI 选项与 `src/util.scm`、
   `src/combine_scm/{calendar,parse}.scm` 在实际二进制里不可用。
   若日后 guile 在制品仓 release，应改为 `requires("guile/...")` 并去掉两条
   `ac_cv_*` 钉死，届时 Test 7 才会进"通过"侧（分母不变）。
4. `--disable-nls` 意味着 `po/` 里的 `de.gmo`/`fr.gmo` 等消息目录不安装；
   `combine` 的界面语言只有英文。目标机上本来也没有 libintl 与 locale 数据面。
5. 配方把 `guiledatedir` 覆盖到 `/share/combine_scm`；若哪天启用 guile，
   `GUILE_SITE` 会由 `guile-config info pkgdatadir` 给出，这个覆盖就应当撤掉。
6. 本包是 `application`，包内没有 `.a/.so`（`lib/` 的 `libdf.a` 是 `noinst_LIBRARIES`），
   所以不适用 R26 的"系统同名库静态化"判定，也不会撞 G3。
7. `share/info/combine.info` 的完整性由配方的 `_info_snapshot`/`_info_verify`/
   `_info_check_packaged` 三个 helper 保证（快照件写在 `self.build_folder`，不落源码树、不入库）。
   换版本时若上游不再自带 `doc/combine.info`，`_info_snapshot` 会直接 `ConanException`
   要求人工处置 ⇒ ⛔ 把它改成静默跳过；若自带件本身是空的，参照确立阶段也会拒绝。
   判据是"解包后一手算出的 size+sha256"，⛔ 换成硬编码 97620。

**最终状态**

- 路径：A（autotools 配方），构建系统零改动源码逻辑；补丁 4 条，全部 portability 类
- 依赖：零 Conan 依赖（guile 可选、NLS 关闭，均有实测依据）
- `conan create`：**通过**（A 机，profile `ohos-aarch64`，`--build=missing`）
- 上游测试：`make check` 在 `build()` 内**真实执行**，7 个用例全执行，**6 通过 / 1 失败**
  （Test 7 = guile 扩展用例，可选依赖未启用；分母未缩、用例未删）
- 消费者测试：`test_package/test.sh` **7/7 通过**（7 个编号节、退出码 + 输出双判据；
  判决行原文见 `reports/w3-local-ci.log:3520`）
- info 交付件：`share/info/combine.info` 97620 B、sha256 与 tarball 原件逐字节相同
  （W68R-COMB-01 整改；判决行 `COMBINE_INFO_INTEGRITY=pre=0 post=97620 sha=90751f24deba restored=true`）
- 货源：`https://ftp.gnu.org/gnu/combine/combine-0.4.0.tar.gz`，
  sha256 `56e71cd9cc38404fc4e6dac02d5fb76e894d481f9be8719072b1f8b1d8afbe14`（设备侧实算）
- 未复证项：CI 流水线（本窗不建 PR、不触发 CI）、跨机（B 机）构建。
  `conan-verify` 的 G0/G1/G2/G3/G4 与 L2/L4/L5 已在收口时复跑（2026-09-26 19:16，全 PASS）


## 路径与知识声明（与 PR 正文逐字同源）
- **适配路径**：路径 A（基础适配）＋ 知识库命中复用（无新增知识条目）
- **使用知识库**：本 worktree 根 `SKILL.md` 及其路由的 `KNOW_YOUR_WHY.md` / `CONTRIBUTING.md` / `docs/TEST_QUALITY_SPEC.md` / `knowledge/ARCHIVE-SPEC.md` / `iron-rules.md`；`scripts/ohc-run.py recipe-search combine` 无同族底稿 ⇒ 命中并复用既有处方条目（每条都先读原文标题与处方再采纳）：`E386` 同族（profile `[buildenv]` 导出的 `CONFIG_SHELL=/data/service/hnp/bin/bash` 在 HMDFS 支撑的构建目录里 `getcwd()` 必挂，autoconf 会用 `$CONFIG_SHELL` re-exec 自己 ⇒ `configure: error: working directory cannot be determined`；处方＝`env -u CONFIG_SHELL SHELL=/bin/sh` **内联前缀** + 树内手工 configure/make，并与 configure 写在同一条命令行里，⛔ 在 `generate()` 期 `env.unset`——运行期会被重新注入击败）；`E011/E114`（autoconf 2.69 的 `config.status` 用 `umask 077` 建 `./confXXXXXX`，HMDFS 落成 `drwx--S---` ⇒ `can't create ./confFUdHCP/subs1.awk: Permission denied`；处方＝改 `umask 002` 而非删掉，删掉后模式取决于环境 umask、不确定。A/B 对照实测：`umask 077` → `drwx--S---` 且写入被拒；`umask 002` → `drwxrws--x` 且写入 OK；`(umask 077 && mkdir)` 的 fallback 分支本来就 OK ⇒ **只有 `mktemp -d` 这条分支炸**）；`E160`＋`E007`（随包 `config.guess` timestamp=`2004-03-12` 不识别 `uname -s`=HarmonyOS ⇒ `configure: error: cannot guess build type; you must specify one`；⚠ **本快照的分支体是 `echo <triplet>; exit 0 ;;` 风格、`grep -c 'GUESS=' config.guess` = 0** ⇒ 仓内 `scripts/patch-autotools-ohos.pl` 产出的 `GUESS=` 形态在这个快照里根本不会被读到（helper 形态只在 2021 重构之后有效），故按**本快照自己的风格**生成成对补丁，并 ⛔ 直接拿别包补丁锚点（本项目实证过 `Hunk FAILED`）；同时 ⛔ 用 `--build/--host` 绕过——那会被判成交叉编译、`AC_RUN_IFELSE` 类探测静默跳过）；`R6`（⛔ 改生成的 `Makefile.in`，安装目录改由 make 命令行变量覆盖）；`E363`（旧式 shell 测试套件的失败不得被报成「上游套件通过」，其处方含「每一次 setup/compile/execute 失败都要显式返回」与「宣告成功前必须有非空结构化摘要 + 生成物」两条）。本包撞上的是它的另一种形态：上游 `tests/test_combine` **没有显式 exit**，脚本最后一条命令是清理用的 `rm ${bld}/testout*.txt ${bld}/stats.txt` ⇒ Test 7 FAILED 时脚本仍以 0 退出，⇒ ⛔ 拿 `make check` 的退出码当判据。因交付纪律不许改上游测试源码，本包按该条处方把判据换成**逐用例点收 stdout 的 `Test N … PASSED/FAILED` 结构化行 + `test_package` 独立逐字节断言**。一手互证：`tests/Makefile:432-433` 的 `check:` 规则体是裸调用、无 `-` 前缀 ⇒ 「退出码 0 来自脚本自身，不是 make 吞错」；W3 日志 `:3240` 是那次 `make -j1 check` 的 RUN 行、`:3298` 是 `Test 7: (Extension load and field modification.) FAILED`，而整段没有 `ERROR: build failed` ⇒ 与「rc 恒 0」互证。`PF5`（补丁新增行不得出现 `__OHOS__`，故摘掉 helper 的 LIBC 探测 hunk，实测 `grep -n "^+.*__OHOS__" patches/*.patch` 为空）。同族已合入先例：`archives/g/gnu-pw-mgr/2.7.4`、`archives/l/luit/20250912`（E386 形状）。
- **知识库扩展**：无新增条目。本包三处"看起来新"的形态都落在既有条目覆盖内，逐条判据写进 `archives/c/combine/0.4.0/notes.md`：①`makeinfo` 缺失面没有用"占位成 `:`"的糊弄法（那条规则会先备份 `$@` 进 `.am$$`、让假 makeinfo"成功"、最后 `rm -rf $$backupdir` **吃掉真 info 件**），也没有停在"压时间戳让规则不触发"（实测该规则仍会被再生的 `version.texi` 触发、缺失的 makeinfo 用 `-o` 把原件截成 0 字节），而是照上游 Makefile 自身的备份/还原形状对账：make 之前快照 tarball 自带 `doc/combine.info` 的原件字节、全部 make 跑完原样写回、再用解包后一手算出的 size+sha256 逐字节断言——属"按上游 Makefile 自身形状规避 + 产物对账"而非新机制；②`guile` 可选依赖的目录退化（`GUILE_SITE` 为空 ⇒ `guiledatedir` 变成 `/combine_scm`）用 make 变量覆盖修，是 R6/既有的"安装目录覆盖"口径；③`tests/test_combine` 的 shebang 由 `#!/bin/bash` 改为 `#!/bin/sh`（本机 `/bin/sh` 是 toybox ash、`/bin/bash` 不存在；实测该脚本用到的 `[[ ]]`/`==` 目标 sh 吃得下，故只改解释器、不动脚本体），属「OHOS 无 FHS 解释器路径」既有族。判 `hit` 不升 `create`。
- **关联 Issue**：无（B 判定=hit，本 PR 不携带 `knowledge/drafts/` 成对草稿、不建知识库扩展 Issue）
---

**编译结束**: 2026-09-26 19:18
**最终状态**: built
