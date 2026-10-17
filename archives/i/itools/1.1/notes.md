# itools 1.1 适配笔记

## 编译环境
- 构建系统: autotools（设备实测 `autoconf (GNU Autoconf) 2.72` + `automake (GNU automake) 1.17`；
  tarball **不带** `configure`/`Makefile.in`/`aclocal.m4`/`install-sh`/`config.guess`，
  须 `autoreconf -f -i` 自举——README「Basic Instructions」官方口径即此）
- 编译日期: 2026-09-25
- 编译器: clang/clang++（OHOS aarch64，os.version 6.0，profile `ci/conan/profiles/ohos-aarch64`）
- 状态: built（W3 `conan create` 结果见下方「验证结果」）

## 编译步骤

```bash
# 依赖（R35 口径，用 download 不用 conan list）
conan download libitl/0.8.0 -r=ohpcd --only-recipe   # 配方在仓
conan download libitl/0.8.0 -r=ohpcd                 # 二进制包亦已发布

# 自举 + 编译 + 分段安装（conan 配方内等价：Autotools.configure/make/install）
autoreconf --verbose --force --install     # 需要 ACLOCAL_PATH 含 pkg.m4，见问题 #1
./configure --prefix=<pkg>                  # --build/--host 不需要，见问题 #3
make -j1                                    # E074：HMDFS jobserver fifo EPERM，禁并行
make install                                # 非 install-strip，见「注意事项」
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 首跑 `./configure` 必挂：`syntax error near unexpected token 'ITL,'` | 设备 aclocal 搜索目录 `~/usr/local/share/aclocal` 只有 cmake.m4/libtool.m4 等，**无 pkg.m4**；`configure.ac:16` 的 `PKG_CHECK_MODULES(ITL, libitl, …)` 未被展开，**原始宏文本原样留在生成的 `configure:4658`**（实测 `grep -c PKG_CHECK_MODULES configure` = 1，且 `pkg_failed`/`PKG_CONFIG_PATH` 计数为 0） | 实测设备上唯一可用的宏文件 = `/data/service/hnp/pkg-config.org/pkg-config_0.29.2/share/aclocal/pkg.m4`（含 `AC_DEFUN([PKG_CHECK_MODULES])`，本 uid 可读，实测 `-rwxr--r--`）。**注入方式要内联**：本配方无 tool_requires 时，`buildenv_info.append_path("ACLOCAL_PATH", …)` 的贡献**不会落地**（实测 `conanbuild*.sh`/`*.conf` 里 `grep ACLOCAL_PATH` 零命中），因此改为把 `ACLOCAL_PATH=<dir>` 直接写进 `autoreconf` 命令行（`env ... ACLOCAL_PATH="…" autoreconf -fi`）。另注：本品 `configure.ac` 无 `AC_CONFIG_MACRO_DIR` ⇒ §970 那条「拷 pkg.m4 进 m4/」的解法在此**不成立**，只有 ACLOCAL_PATH 可行 |
| 2 | `AC_PROG_INSTALL` 被注释（`configure.ac:12`）会不会让 `make install` 失配 | **不成立，已证伪**。`AM_INIT_AUTOMAKE()`（第 6 行）经 aclocal 展开后，`aclocal.m4:439` 明确写着 `AC_REQUIRE([AC_PROG_INSTALL])dnl` ⇒ 宏仍会运行，`INSTALL/INSTALL_PROGRAM/INSTALL_SCRIPT/INSTALL_DATA` 正常替换；`autoreconf` 输出亦见 `configure.ac:6: installing './install-sh'` | 不打补丁（零源码修改）。OHOS 上没有 `install` 命令这一事实由 AC_PROG_INSTALL 自己的 `install-sh` 兜底分支处理（实测 `configure` 内含 `ac_install_sh="…install-sh -c"` 逻辑）。sct 初筛写的行号是 `:7`，实际在 `:12` |
| 3 | 要不要按 §12.1 传 `--build/--host` 三件套 | 不需要。`autoreconf -i` 确实补进了 `config.guess/config.sub`（实测 `configure.ac:30: installing './config.guess'`），但本机 `sh ./config.guess` 实测返回 `aarch64-unknown-linux-ohos` ⇒ 现代 config.guess 认得 HarmonyOS。按 R1「参数最少化」只留 `--prefix` | 不传三件套；若 CI worker 的 config.guess 版本不同导致 `cannot guess build type`，再按已合入的 abiword-plugin-* 写法补显式三元组 |
| 4 | `AM_INIT_AUTOMAKE()` 空参 = GNU 严格度，包内独缺 `INSTALL` 文件 | GNU 严格度要求 AUTHORS/COPYING/ChangeLog/NEWS/README/**INSTALL** 齐在，包内只有前五个 | `autoreconf` 必须带 `-i`（`--add-missing`）：实测 `Makefile.am: installing './INSTALL'` 自动补出。只 `-f` 不 `-i` 会在 automake 阶段失败 |
| 5 | CI 沙箱缺 automake/aclocal；工具内部路径烧死 | 与已合入的 abiword-plugin-* 同一环境事实：沙箱只有 `/data/service/hnp/bin` 的 autoconf 套件 | `tool_requires("automake/1.18")`（归档树实有 1.16.5/1.17/1.18）+ `_prepare_autotools_env()` 按 PATH 回填 `AUTOCONF/AUTOHEADER/AUTOM4TE/SED` |
| 6 | `Makefile.am` 的 `*_LDADD` 硬编码 `-litl -lm`，且不引用 `@ITL_CFLAGS@/@ITL_LIBS@`；但直接上 `AutotoolsDeps` 又炸 | `AutotoolsDeps` 会把依赖闭包写进 **LIBS**，于是 autoconf **最早**那个 run 探针（`checking whether we are cross compiling`）就无条件链 `-litl`，而 `libitl.so` 的搜索路径在 conanrun 侧、构境内没有 ⇒ `config.log` 实锤：`./conftest` → `Error loading shared library libitl.so` → `$? = 127` → `configure: error: cannot run C compiled programs`（E467） | **不生成 AutotoolsDeps**（E467 的 fallback），只把 `-I/-L` 走 `tc.extra_cflags/extra_ldflags`，不注入 LIBS；链 `-litl` 由 Makefile.am 自己的 LDADD 提供。不改静态、不预设 `cross_compiling`、不加 `--host`（E467 明文三禁） |
| 7 | ★`configure: error: cannot guess build type; you must specify one`，但其**上游**报的是 `configure[N]: ac_fn_c_try_link: command not found` | **conan 的 `automake/1.18` 包提供的 aclocal 宏与本机 `autoconf 2.72` 混配**，使 autoconf 生成的 configure 把 C 链接辅助函数 `ac_fn_c_try_link ()` 的定义（实测 L4962）**排在了首次调用（实测 L1724）之后** ⇒ 调用点是未定义符号。判别 A/B（同一份 `configure.ac`，只换工具来源）：设备 `autoconf 2.72 + automake 1.17` 生成的顺序正确（定义 L1526 < 调用 L1755），换 conan 1.18 的 aclocal 就颠倒 | **不声明 `tool_requires("automake/...")`**，用 profile `[buildenv]` 已前置的 `~/usr/local/bin` 设备套件（autoconf 2.72 + automake 1.17，配对已实测可用）。⚠ 知识库里的 `cannot guess build type` 条目（E007/E072/E160、§12 的 217/1043/1144 行、配送表 M4）**全部是"老 config.guess 不识 HarmonyOS"这一因**，解法是显式传三元组；照它做会**盖住**本条真因。鉴别只看一处：先看这条 error 之前有没有 `ac_fn_c_try_link: command not found`，或直接 `grep -n "^ac_fn_c_try_link ()" configure` 与首次调用行号比大小。详见 `knowledge/drafts/DRAFT-itools-1.1-autotools-mixed-toolchain-pairing.{kv,md}` |

## 源码修改

**无补丁，零上游源码改动。** 上面问题 #2 的 standby 补丁（`configure.ac` 取消注释 `AC_PROG_INSTALL`）
经真机证伪为不需要；问题 #6 的 standby 补丁（`Makefile.am` 加 `AM_CFLAGS=-DPACKAGE_NAME=…`）
亦不需要——`autoreconf -f` 驱动的 autoheader 已把 `config.h.in` 重写并含
`#undef PACKAGE_NAME`（实测 `grep -cE 'PACKAGE_(NAME|VERSION|STRING)' config.h.in` = 3）。

## 依赖版本

| 依赖 | 版本 | 来源核验 |
|---|---|---|
| libitl | 0.8.0 | `conan download libitl/0.8.0 -r=ohpcd` 成功（配方 + **二进制包**均已在制品仓）。实物头布局 `<缓存>/p/include/itl/{hijri,prayer,astro}.h` ⇒ 与本品 `#include <itl/…>` 前缀一致；`PkgConfigDeps` 能生成 `libitl.pc`（名与 `PKG_CHECK_MODULES(ITL, libitl)` 对齐）⇒ **无 R36 依赖阻塞** |

### 上游测试清点证据（R51 / 五维账本）

| 维度 | 值 | 取证方法 |
|---|---|---|
| `N_static` | **0** | 双法独立：①解包后 `grep -niE "TESTS\|check_PROGRAMS\|add_test\|AM_TESTS" Makefile.am configure.ac` **零命中**，全树无 `t/`、`tests/`；②上游仓 `arabeyes-org/itools@master` 的 `Makefile.am`（raw 抓取）除多一行 `AM_CFLAGS` 外与包内件同构，同样无测试注册 ⇒ 属「上游从未注册测试」，不是漏编/漏注册 |
| `N_registered` | 0 | 无 `TESTS` ⇒ automake 不生成 check 目标 |
| `N_executed` | 0 | 无入口可执行 |
| 未执行/跳过 | 0 | 分母本身为 0（非「有条件未跑」） |
| `N_consumer` | **1 程序 / 12 断言** | `test_package/smoke.c` → `itools_smoke`：真实编译成 ELF（不写 shell 脚本，避开 CI 拒跑 shebang）、`popen` 起安装后的 `ical`/`idate`/`ipraytime`，断言退出码与输出结构；`failures!=0` 时返回 1 |

断言清单（T4 的退出码是上游源码写死的：`usage(1)` 在 ical/idate 里 `exit(20)`、ipraytime 里 `exit(10)`）：

1. `ical --gregorian 20260924` 退出码 0；2. 其输出含日期数字与 `/`；3. `idate --gregorian 20260924` 退出码 0；
4. `idate` 输出的回历日期落在合理区间；5. `ipraytime --date/--latitude/--longitude/--utcdiff` 退出码 0；
6. `ipraytime` 输出含 `hh:mm` 时刻；7-9. 三个程序的 `--help` 退出码 20/20/10；
10. 用 T4 得到的回历日期反算退出码 0；11. **反算回公历 == 24/9/2026（G2H↔H2G 往返闭合）**；
12. `ical --gregorian --hijri` 互斥参数干净非零退出（信号死亡记 -1 判 FAIL）。

第 11 条是本品最强的功能性断言：它证明链接到的 libitl 真在计算，而不是"打印了点什么"。

## 验证结果

```bash
# W3 / conan-verify（G0-G4 + L2/L4/L5）：全绿，2026-09-25T13:28 报告 Verdict: PASS
#   参考 `itools/1.1@ohpcd/stable`，profile ohos-aarch64（-pr:b 与 -pr:h 同档 ⇒ cross_building=false）
# 命令：python3 scripts/ohc-run.py conan-verify itools 1.1   →   VERIFY_RC=0
#   G1 配方完整性 PASS / G0 预构建风险 PASS / G2 conan create PASS / G3 系统同名库隔离 PASS / G4 产物完整性 PASS

# 消费者测试（test_package/smoke.c → itools_smoke，真编译 + 真运行）
$ ./itools_smoke
itools smoke: 12 checks, 0 failures        # 12/12 全通过

# 被测二进制实测（各跑一次）
$ ical --gregorian 20260924
     Rabi II 1448 (A.H)
  S  Ah   I   T  Ar   K   J
          1   2   3   4   5
  6   7   8   9  10 [11] 12
 ...                                        # RC=0；回历 1448-03(Rabi II)-21 与 T11 反算自洽
$ idate --gregorian 20260924               # RC=0，输出 "+ Output   : 21/ 3/1448"
$ ipraytime --date 20260924 --latitude 24.4667 --longitude 54.3667 --utcdiff 4
                                            # RC=0，输出含 Qibla 与 hh:mm 时刻

# 内存预算（§14.1④，memcap-run.py --probe 实测峰值 RSS）
#   ical 0MB / idate 0MB / ipraytime 4MB ⇒ 全量消费者测试预算 256MB 足够
# ELF 自签（E077）：llvm-readelf -S 对 ical/idate/ipraytime 的 .codesign 段计数均 = 1
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/ical | 27008 B | 回历月历表（链 libitl + libm，已自签） |
| bin/idate | 22912 B | 公历↔回历转换（已自签） |
| bin/ipraytime | 39360 B | 礼拜时刻与 Qibla 计算（已自签） |
| bin/ireminder | 13964 B | 上游 perl 脚本（见「注意事项」，不计入通过率） |
| share/man/man1/{ical,idate,ipraytime,ireminder}.1 | — | 4 份 man 页（`man_MANS`） |
| licenses/COPYING | — | arabeyes 免责声明原文 |

## 注意事项

- **`ireminder` 随包交付但不执行**：shebang 写死 `#!/usr/bin/perl`，OHOS PC 无 perl 运行时 ⇒
  它是 `bin_SCRIPTS` 的交付物但不计入通过率，12 条消费者断言只覆盖 3 个 C 程序。
  为凑数给它写断言=造假，不做。
- **打包禁止 strip**：用 `make install` 而非 `install-strip`。`strip` 会剥掉 clang 链接期嵌入的
  ad-hoc `.codesign` 段，被剥副本在设备上 `Operation not permitted`（E077 新触发场景）。
- **ELF 自签**：`package()` 对 `bin/*` 走 E077 四步（`--remove-section .codesign` →
  `binary-sign-tool -selfSign 1`），且调用签名器必须 `env -u LD_LIBRARY_PATH`（§12.14：
  SDK 的 libc++ 会劫持 `binary-sign-tool` 的 `std::__h` 符号，报 symbol not found / exit 127）。
  非 OHOS / 工具不存在 / 单文件失败三类情形只告警不中断（`self.run(..., ignore_errors=True)`
  才拿得到返回码——默认失败即抛，写 `if ret != 0` 是死代码）。
- **`AC_CHECK_LIB([itl],[getNorthQibla])` 是 PKG_CHECK_MODULES 的回退分支**：修好 pkg.m4 后走的是
  pkg-config 主路，该回退不再触发；两个库名（`itl`/`m`）与 libitl 的 `cpp_info.libs/system_libs` 一致。
- **版本串差异**：tarball 是 1.1（`NEWS` 首段即 "Changes in itools-1.1"），但 `configure.ac:5` 的
  `AC_INIT([itools],[1.0])` 未跟着升 ⇒ `PACKAGE_VERSION` 与 man 页文字仍是 1.0。本品无 `--version`
  选项 ⇒ 不产生用户可见的版本差，归档目录/分支/conan 版本一律按任务口径 1.1，不改上游版本串。
- **ipraytime 不依赖 rc 文件**：`get_rcfilename()`(`:354`) → `process_file()`(`:134`) 打不开文件时
  `return 1`，而调用点 `:417-418` **忽略返回值** ⇒ 无 `~/.iprayrc` 时用内置默认值，只有显式 `--file`
  缺失才致命（`:471`）。所以 CI 环境下不需要预置 rc 文件。
- **B 判定**：`hit(E338)`（getpwuid/pw_dir 族，`ipraytime.c:296 get_homedir()` 首选分支就是 E338
  推荐的 `getenv("HOME")`，回退分支 `:313` 已判 `!p` ⇒ NULL 干净退出，不 SIGSEGV）。
  本 PR 不携带知识草稿。上轮登记的机制候选「AC_PROG_INSTALL 缺位 ⇒ @INSTALL@ 未替换」
  已被 `aclocal.m4:439` 的 `AC_REQUIRE` **证伪**，故不落 `B草稿库/`（避免 §6.2⑦ 第 3 条禁止的空走）。

### 顺序与取证出处（供复核）

- `aclocal.m4:439` = `AC_REQUIRE([AC_PROG_INSTALL])dnl`（证伪问题 #2）
- `configure:4658` = 残留的 `PKG_CHECK_MODULES(ITL, libitl, ,`（坐实问题 #1）
- `config.h.in:59` = `#undef PACKAGE_NAME`（证伪 standby 补丁 #2）
- `sh ./config.guess` → `aarch64-unknown-linux-ohos`（定档问题 #3）
- ACLOCAL_PATH 注入顺序与 `_prepare_autotools_env()`、`-j1`、`PKG_CONFIG_PATH=generators_folder`
  三处写法照抄已合入的 `archives/a/abiword-plugin-{clarisworks,docbook}/3.0.8/conanfile.py`
- E114 的 `umask 077` 陷阱在本品生成的 configure 中**计数为 0** ⇒ 不引入 abiword 那段 `_drop_umask_077`
## 方案 A 落地与一次自我证伪（2026-09-29，new_hw-10）

### A 的形态：预生成件随配方导出，构建期零 bootstrap

CI（PR #12629 build 60809，失败步 `conan-build-test`，前 5 步与 cleanup 全绿 ⇒ 配方类）第一条真实错误逐字：

```
Can't exec "aclocal": No such file or directory at
  /data/service/hnp/autoconf.org/autoconf_2.72/share/autoconf/Autom4te/FileUtils.pm:299
autoreconf: error: aclocal failed with exit status: 2
```

物理判据（设备实测，非推断）：worker 侧 PATH 形态下 `autoreconf`/`autoconf` 可解析（hnp），
而 `aclocal`/`automake` **无对应物**（`/data/service/hnp` 下无 automake 目录）。 ⇒ 凡在 `build()` 里跑
autoreconf 的写法在该 worker 上必崩，而本包 tarball 本身不带 `configure`（官方 README 口径即 `autoreconf -f -i`）。

采方案 A：configure 及辅助件由本机预生成、随配方导出，构建期不调用任何 autotools bootstrap。
导出形态照**已合入**的 `archives/l/libxmi/1.2`（`compat/`）与 `archives/a/afflib/3.7.22`（`generated/`），
非本包自创。落位 `archives/i/itools/1.1/generated/` 共 11 件：

| 文件 | 字节 | sha256(前 16) |
|---|---|---|
| configure | 206793 | 48d385462ecca4b7 |
| config.h.in | 2384 | 828dea483352274c |
| Makefile.in | 31001 | c6e54faf56c6fef0 |
| aclocal.m4 | 58893 | d6c8395bc94d1be5 |
| config.guess | 51014 | d7e181b8b8215278 |
| config.sub | 36660 | 41bb136da93f7ae3 |
| install-sh | 15437 | 250865025dcfc1b5 |
| missing | 7728 | 1509d72c676d3b75 |
| compile | 7621 | 07089708e9aba8bc |
| depcomp | 23695 | 62cde010a373e569 |
| INSTALL | 16377 | a32a373565a5284c |

配方改动四处（其余一律不动）：`exports = "generated/*"`；`export_sources()` 增 `copy` 到
`export_folder/generated`；`source()` 增 `_restore_pregen()`（按候选目录定位导出件 → `shutil.copy2`
放回源码树 → 复用 `_restore_script_modes()` 恢复执行位，缺 `configure/Makefile.in/config.h.in` 即硬失败）；
`build()` **删除** `autoreconf` 调用，改为"无 configure 即抛 `ConanException`，绝不静默回退现场自举"。
`build_requirements()` 维持零 `tool_requires`。

生成命令与 `build()` 原第 201 行完全同形（关键在 `ACLOCAL_PATH` 必须指向含 `pkg.m4` 的目录）：

```
env -u CONFIG_SHELL SHELL=/bin/sh \
  ACLOCAL_PATH=/data/service/hnp/pkg-config.org/pkg-config_0.29.2/share/aclocal \
  autoreconf --verbose --force --install
```

### 一次自我证伪：旧稿的归因与"好生成物"证据都不成立

本机上一轮（2026-09-27）留在 `~/tmp/uc2/hw-10/pgen/` 的那份 configure **不可用**，本轮复测坐实：

- 它未带 `ACLOCAL_PATH` ⇒ `PKG_CHECK_MODULES` 原始宏文本残留在第 4658 行，
  `sh -n configure` 直接在该行报 `syntax error: unexpected 'ITL,'`（退出 1）。
- 旧稿据"定义 1526 早于调用 1755"把它当作**顺序正常的合格生成物**——该证据作废：一份连 shell 语法都过不了的
  件不能证明任何顺序形态。**判 autotools 生成件是否可用，硬判据是 `sh -n` 通过，不是函数行号先后。**

进一步的单变量最小复现（15 行 `configure.ac`，纯 `autoreconf`，不编译、不占构建槽；
两组同为 autoconf 2.72 + automake 1.17 同族、同 `ACLOCAL_PATH`）：

| 组 | 差异 | 首调用行 | 首定义行 | 定义块数 | 形态 |
|---|---|---|---|---|---|
| P | 含 `PKG_CHECK_MODULES(ITL, libitl, [], [AC_CHECK_LIB(...)])` | 1537 | 4594 | 2 | 定义后置 |
| Q | 其余逐字相同，仅把该宏换成等价 `AC_CHECK_LIB` | 1568 | 1477 | 1 | 定义前置 |

⇒ 触发变量是 **`PKG_CHECK_MODULES`（pkg.m4）宏展开本身**，与"conan automake/1.18 与本机 autoconf 混配"无关；
旧稿 `DRAFT-itools-1.1-autotools-mixed-toolchain-pairing` 的因果不成立，已改写为
`DRAFT-itools-1.1-pkg-check-modules-try-link-late-definition.{kv,md}`（同 PR 成对提交）。

### 顺带暴露的产物层失真（先于本改动存在，非 A 引入）与影响判定

本轮第一腿日志（`~/tmp/uc2/hw-10/logs/new_hw-10-leg1-20260929-204946.log`，经 `SLOT_EXTEND` 取第 3 槽，
`MemAvailable 8875MB >= 8000MB` 在 §14.1① 硬上限内）中 `conan create` **退出 0**，但 configure 段有 4 处：

```
checking for pow in -lm...        configure: line 5065: ac_fn_c_try_link: command not found
checking for error_at_line...     configure: line 5283: ac_fn_c_try_link: command not found
checking for alarm...             configure: line 1724: ac_fn_c_try_link: command not found
checking for strcasecmp...        configure: line 1724: ac_fn_c_try_link: command not found
```

后果是 `config.h` 里 `HAVE_ALARM`、`HAVE_STRCASECMP`（及 `error_at_line` 族）成假阴性；
而由 `try_compile`/`try_run` 完成的探测正常（`the C compiler works... yes`、`cross compiling... no`、
`GNU libc compatible malloc... yes`）——这正是它容易被全绿掩盖的原因。

影响判定（不是猜测，逐条数过）：上游 `ical.c`/`idate.c`/`ipraytime.c` 对 `HAVE_STRCASECMP`、`HAVE_ALARM`、
`HAVE_ERROR_AT_LINE` 的引用数**均为 0**；全包条件编译点仅 5 处，只消费 `TM_IN_SYS_TIME`（3 处）与
`HAVE_TM_GMTOFF`（1 处）+ `DEBUG`（1 处），这两个宏都不是本条误探测的产物。
⇒ **本次失真不改变交付二进制行为**，按"已知限制"如实申报；同轮 `test_package` 12 条行为断言全部通过
（含回历↔公历往返闭合，证 libitl 真被链上并算对）。若某包上游确实消费这些宏，则不得照原样交付，
须消除 `PKG_CHECK_MODULES` 展开路径后复测。

零 bootstrap 的可复核凭据：该日志内 `autoreconf|automake` 命中数 **0**；唯一的 `aclocal` 字符串是
`Copied 2 '.m4' files: aclocal.m4, aclocal.m4`（导出件拷贝，非执行）。
---

**编译结束**: 2026-09-29 21:08
**最终状态**: built
