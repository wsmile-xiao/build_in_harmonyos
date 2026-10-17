# mcds 1.9-git20260415 适配笔记

> **生成物口径（2026-09-29 按审查意见统一）**：本文件所有 `archives/m/mcds/1.9-git20260415/reports/*` 引用（`.log` / `*.md` / `*.json` / `.txt`）**均按 §19 不随 PR、磁盘留档**，行号与 sha 指构建主机/工作区留档原件；PR 内只保留本文件与 PR 正文中的读数。


## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-26
- 编译器: clang/clang++（目标三元组 aarch64-unknown-linux-ohos，OHOS musl）
- 状态: built

货源是上游 GitHub 的**提交归档**（git snapshot，2026-04-15 当日 tip 提交
`0e150e90439bac5b306f5ca17091db4a300b76b2`），不是 release 产物：`tar tzf` 实测
归档里只有 `configure.ac` / `Makefile.am` / `po/Makefile.in.in`，**没有**
`configure`、`Makefile.in`、`config.guess`、`aclocal.m4` ⇒ 配方必须在 `build()`
里 `autoreconf -fi` 自举。该快照的 `AC_INIT` 仍是 `1.8`，所以 `mcds --version`
打印 `mcds (GNU mcds) 1.8`；任务版本串按快照日期命名，二者不是同一坐标（四处
版本串一律用 `1.9-git20260415`）。

## 编译步骤

```text
1) conan source()         get(..., strip_root=True)  顶层目录 mcds-0e150e90...
2) apply_conandata_patches 1 枚：src/main.c 的 program name 兜底
3) autoreconf -fi          在 source 目录内现场生成 configure / Makefile.in /
                           build-aux / m4 / aclocal.m4
                           （ACLOCAL_PATH 前置 gettext 包 share/aclocal，
                             gettext_datadir 指到包内 share/gettext）
4) 文本剥离 configure      去掉 AS_TMPDIR 的 `umask 077 && mktemp -d`、
                           `umask 077 && mkdir`（HMDFS setgid，见问题 3）
5) ./configure             --build=aarch64-unknown-linux-ohos
                           --host=aarch64-unknown-linux-ohos
                           --disable-dependency-tracking --disable-nls
                           --disable-gpgme --disable-libsecret
6) make -j1 ACLOCAL=: AUTOCONF=: AUTOHEADER=: AUTOMAKE=: MAKEINFO=:
7) make install            （同一组空工具变量）
```

**in-tree 构建**（配方不调 `basic_layout`）：见问题 2。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 成功后 `make` 退出码 2，日志 `make: *** [Makefile:392: aclocal.m4] Error 127` + `WARNING: 'aclocal-1.17' is missing on your system` | automake 生成的 maintainer-mode 重生成规则用的是**带版本号**的工具名（`build-aux/missing aclocal-1.17` / `automake-1.17`），而 tool_requires 与构建主机 PATH 只提供不带版本号的 `aclocal`/`automake`；`missing` 包装脚本找不到就 exit 2 | 向 `make`/`make install` 传空工具变量 `ACLOCAL=: AUTOCONF=: AUTOHEADER=: AUTOMAKE=: MAKEINFO=:`，把 maintainer 规则变成 shell 空操作。不改货源、不跑第二遍 autoreconf（实测同一棵已 configure 的树：裸 make `RC=2` → 喂空变量后 `RC=0`） |
| 2 | `src/main.c:29:10: fatal error: 'config.h' file not found` | automake 给本树生成的 `DEFAULT_INCLUDES` 是**空的**（实测 in-tree 构建树内 `src/Makefile:140 DEFAULT_INCLUDES =`；该行的**路径前缀**早期写作 `build-release/`，系 out-of-tree 探索轮读数、收口改 in-tree 后未同步，本行已更正；**行号 140 实测正确**，但 automake 生成物的行号会随 automake 版本漂移 ⇒ 复算请用 `grep -n "^DEFAULT_INCLUDES" <构建树>/src/Makefile` 而不是钉死行号），`#include "config.h"` 只能靠"与 main.c 同目录"这条 quoted-include 规则命中；VPATH(out-of-tree) 下 main.c 取自 srcdir、config.h 生成在 builddir，两者不同目录 | 去掉 `basic_layout`，把 build 目录压回源码目录做 **in-tree** 构建（上游自己的 CI 也只跑 `./configure && make`，本就不支持 VPATH） |
| 3 | configure 期 `can't create ./confXXXXXX/subs1.awk: Permission denied` | HMDFS 对目录强制 setgid：`AS_TMPDIR` 用 `(umask 077 && mktemp -d)` 建出的 `drwx--S---` 临时目录连创建者都写不进 | 运行 configure 前对生成脚本做文本剥离（`configure` 是现场生成的，交付不了 patches/ 补丁，故与 adcli/avahi-tools 同法在配方内处理） |
| 4 | `config.guess` 认不出 HarmonyOS | `uname -s` = `HarmonyOS`、内核串 `HongMeng Kernel`，GNU config.guess 无该分支 | 显式传 `--build/--host=aarch64-unknown-linux-ohos`（`config.sub` 支持 `*-linux-ohos`），不去改 config.guess |
| 5 | `--help` 打印 `usage: unknown ...` | 上游 `program_name()` 依赖 `getprogname()` 或 `program_invocation_short_name`，OHOS musl **两者都没有**（实测 `src/config.h`：`/* #undef HAVE_GETPROGNAME */`、`/* #undef HAVE_PROGRAM_INVOCATION_SHORT_NAME */`），于是落到字面量 `"unknown"` | 补丁 `patches/0001-src-main.c-progname-fallback.patch` 增加 BSD `__progname` 全局量兜底（实测 OHOS musl 导出该符号，探针 `pp.bin` 可链接可运行） |
| 6 | GPGME / libsecret 两条后端 | `configure.ac` 在启用 GPGME 时强制要求宿主存在 `gpgconf` + `gpg`（`AC_PATH_PROG` 找不到即 `AC_MSG_ERROR`），构建主机两者皆无；`libsecret` 制品仓无配方且其后端是 Secret Service D-Bus 接口 | `--disable-gpgme`、`--disable-libsecret`；`mcds --version` 的编译期回显 `with-out GPGME support` / `with-out libsecret support` 由消费者测试 T2b 断言，确认裁剪真的进到了产物 |
| 7 | `AM_GNU_GETTEXT([external])` 的宏与数据目录 | 提交归档不含 `m4/`，`aclocal` 取不到 `gettext.m4`；`autopoint` 也要 gettext 数据目录 | `tool_requires gettext/0.22.5.1`，并把 `ACLOCAL_PATH` 前置到该包 `share/aclocal`、`gettext_datadir` 指向包内 `share/gettext`（avahi-tools 同源做法）；`--disable-nls` 另因 `po/` 只有模板 `mcds.pot`、无任何 `.po` 翻译 |

## 源码修改

仅 1 枚补丁，已在 `conandata.yml` 注册、`manifest.yaml` 的 `patches_applied` 登记：

- `patches/0001-src-main.c-progname-fallback.patch` — `src/main.c` 的
  `program_name()`：在 `HAVE_GETPROGNAME` / `HAVE_PROGRAM_INVOCATION_SHORT_NAME`
  两条都不成立时，改读 BSD `__progname` 全局量，避免 usage/version 打印 `unknown`。

`configure`、`config.guess`、`Makefile.in` 一类**生成物一律不打补丁**：它们由
`autoreconf -fi` 现场生成，补丁交付不了，相应规避放在配方里做（问题 2/3/4）。

## 依赖版本

| 用途 | 包 |
|------|----|
| 运行期（`requires`） | curl/8.15.0、libxml2/2.15.3 |
| 构建期（`tool_requires`） | automake/1.18、libtool/2.5.4、gettext/0.22.5.1 |

运行期依赖是真实的动态链接依赖：在 conan 环境之外直接执行
`<pkg>/bin/mcds` 会报 `Error loading shared library libcurl.so` /
`libxml2.so.16`，必须带 conan 的 `conanrun`（LD_LIBRARY_PATH）。

## 验证结果

```text
$ bash ci/scripts/preflight_check.sh mcds/1.9-git20260415                  RC=0
  [OK] 已发布: automake/1.18 curl/8.15.0 gettext/0.22.5.1 libtool/2.5.4 libxml2/2.15.3
  [OK] 版本号未被占用: mcds/1.9-git20260415

$ conan list "mcds/1.9-git20260415*"      # 跑前先清空本地，保证不是 Cache 蒙过
  Found 0 pkg/version recipes matching mcds/1.9-git20260415* in local cache

$ sh ~/tmp/uc2/build-slot.sh --kind short --mem 2500 --wait 1800 -- \
    python3 scripts/ohc-run.py conan-verify mcds 1.9-git20260415           VERIFY_RC=0
  G1: PASS   G0: PASS   G2: PASS   G3: PASS   (R26 无系统同名库冲突)

  reports/conan-create.log 关键行（共 421 行）：
  :93   mcds/1.9-git20260415@ohpcd/stable#…:fb3d1258… - Build
  :112  Building from source
  :122  Calling build()
  :123  Apply patch (portability): main.c: OHOS musl provides neither getprogname() …
  :124  RUN: autoreconf -fi
  :168  HMDFS umask 077 剥离：mktemp=1 mkdir=1
  :270  RUN: make -j1 ACLOCAL=: AUTOCONF=: AUTOHEADER=: AUTOMAKE=: MAKEINFO=:
  :298  Calling package()
  :382-420  PASS T1 / T1b / T2 / T2b / T3 / T4 / T5a / T5b / T6
            MCDS_TEST_SUMMARY total=9 passed=9 failed=0
  真实编译行 grep -c "ohos-clang" = 22
```

上游成体系测试 **0 条**（本提交没有测试套件：无 tests/、`Makefile.am`/`src/Makefile.am`
不声明 `TESTS`/`check_PROGRAMS`、上游 CI 无测试步骤），逐字机器证据见
`reports/upstream-test-scan.txt`；因此**没有** `make check` 可跑，上面 9/9 全部是
`test_package/` 的消费者测试。申报口径与实测口径同为 9，差集为空；
五维账本与门禁回执见 `reports/test-report.md`。

## OHOS 能力面实测（本包相关部分）

- `termios`：`tcgetattr` 与 `tcsetattr`（`TCSANOW`/`TCSADRAIN`/`TCSAFLUSH`）在 pty
  从端**全部可用**，`ECHO` 标志能真实翻转；`TIOCGWINSZ` 可用。
  ⇒ mcds 的口令交互路径（`src/prompt.c`：`fopen("/dev/tty","w+")` +
  `tcsetattr(fd, TCSAFLUSH, ...)` 关回显）在本平台**没有**被 termios 挡住。
- `open("/dev/tty", O_RDWR)` 在**无控制终端**的会话里返回 `ENXIO(6)`
  （`No such device or address`），设备节点本身存在（`crw-rw-rw- root root 5,0`）。
  这是 POSIX 常规行为，不是鸿蒙特有；对应在真终端里跑的 `-p` 交互取口令才有意义。
- 同一次探针里 `tcflush()`/`tcdrain()`/`tcflow()` 三个接口在 pty **主端和从端一律
  返回 `EPERM(13)`**（`/dev/null` 上的 `tcflush` 返回 `ENOTTY(25)`，是标准行为）
  ⇒ 鸿蒙屏蔽的是 tty 队列控制类操作，而**属性读写不受影响**。
  **mcds 不使用这三个接口**（全量 `grep -rn "tcflush\|tcdrain\|tcflow" src/` 无命中），
  所以该现象对本包**无功能影响**，只是记录给后续终端类软件参考。
- `/tmp` 在本机是只读文件系统；`TMPDIR=/storage/Users/currentUser/tmp` 才是可写临时目录。

## 注意事项

- **本包只支持 in-tree 构建**（问题 2）。若后续有人给配方加回 `basic_layout` 或
  `build_folder`，会在 `make` 阶段以 `fatal error: 'config.h' file not found` 复发。
- **`make` 必须带那 5 个空工具变量**（问题 1）。构建主机上 automake 的
  maintainer-mode 规则一旦触发就 `Error 127`；这不是"构建主机没装 autotools"，
  tool_requires 已提供不带版本号的工具。
- **上游 rc 配置读取在本构建上不生效**（实测，非推断）：
  `-c <file>` 与默认 `$HOME/.mcdsrc` 两条路径下，`url` 键都读不进来
  （`-v` 回显 `URL : (null)`）；写 `username rcuser` 时 `-v` 回显变成
  `Username          : 100`（明显的错值，疑为 `read_rc()` 里
  `char *vals[2]` 在三个及以上 token 时被 `vals[i]` 越界写）。
  **未在 glibc 机器上做对照** ⇒ 本笔记只记现象、不定性为鸿蒙问题，也不据此建
  "无法适配" 类 Issue。因此消费者测试**不含** rc 解析断言（原先那条 T5 断言的是
  一个并不会发生的行为，已按实测改成查询字段断言）。
- 交付的是纯命令行程序：`bin/mcds` 一枚可执行 + `share/man/man1/mcds.1`，
  无库、无头文件；`commands.json` 落在**软件级** `archives/m/mcds/commands.json`。
- `mcds --help` 与 `--version` 的退出码是 **1** 而不是 0（上游 `print_usage()`/
  `print_version()` 都以 `exit(EXIT_FAILURE)` 收尾），脚本判等时不要按惯例写 0。


## 收口披露（主理-74，2026-09-27，W4 r1 整改）

- [E490 属真 N/A] G0 段报的「已知风险 E490 未在配方中处理」对本包不成立，依据不是"构建过了所以没事"：E490 的处方是
  `chmod +x configure config.guess config.sub install-sh missing`（restore-known-autotools-script-modes），而本包
  `reports/upstream-test-scan.txt` 的 [02] 段逐条枚举（实测 47 条）里**没有任何 `build-aux/` 条目、也没有 `configure`**（[02] 段逐条枚举的第 10 条是 `./configure.ac`，属 autoconf 输入而非被 chmod 的脚本载体；序号一手复算 `sed -n '9,55p' reports/upstream-test-scan.txt | grep -n '^\./'` 的第 10 行）
  ⇒ 这些脚本全部由 `build()` 的 `autoreconf -fi` 现场生成（同一日志 `RUN: autoreconf -fi`），归档里不存在"保内容丢执行位"的
  载体。已把 E490 追加进版本级 `manifest.yaml` 的 `knowledge_ref` 并在本行留痕（判据：ref 须与条目同一行）。
- [3 份 reports 是 force-add 的例外] `reports/` 被仓根 `.gitignore:96` 通配排除，本包入库的 `test-report.md`、
  `conan-verify-report.md`、`upstream-test-scan.txt` 三件**原为** `git add -f` 的有意例外；**2026-09-29 按审查意见已全部 `git rm --cached` 撤出 PR、磁盘原件保留，后续任何人重提该目录时普通
  `git add archives/m/mcds/...` 对它们**静默不生效** ⇒ 复提必须同样带 `-f`，⛔ 误当"已入库"。
- [锚点可读性] 本 notes 与 `test-report.md` 里指向 `reports/conan-create.log` 的行号（:93 :112 :122 :123 :124 :168 :270
  :298 :382-420 与 `grep -c "ohos-clang"` = 22）指向的是**构建主机侧日志、本仓不入库**（该件盘上 27231 B / 421 行 /
  `sha256 715122e8fefdfda91762728f7b1bf208eaf6ced814d20b5682f72054fe84e2e3`）⇒ 评审若打不开这些锚点，属"引用了仓外件"，
  请按本行给出的字节数与哈希在有设备权限时复算，⛔ 判成本包缺证据。
- [一处已知未改的同类误名] `conanfile.py` 的 `layout()` 注释里仍写着早期路径 `build-release/src/Makefile:140`。
  **本窗故意不改它**：`conanfile.py` 属导出件，改一个字节就换 recipe revision ⇒ W3 判决与全部行号锚作废、还要全量重审；
  该注释不改变构建行为，按「不为纯文本 P2 换 RREV」的既有口径留给下一次实质改动。

## 发现与知识

本节按版本级 `manifest.yaml` 的 `knowledge_ref` 逐条交代**本包与它的实际关系**：
`applied` = 本包构建/运行面确有该机制的一手读数；`consulted` = 取参考点但本包未触发；`n/a` = 经实测判定不适用（判定依据同注明）。

- ✅ E203 **applied**：musl 无 `getprogname()`/`program_invocation_name` 而提供 `__progname` ⇒ 本包补丁 0001 即按此改 `program_name()` 的取值路径（一手：补丁前 `--help` 打印 `usage: unknown ...`，见 `conandata.yml` 的 `patch_description` 与「遇到的问题与解决方案」表第 5 行；补丁落地实物见构建树 `src/main.c:366-370` 与 `src/config.h` 的两枚 `#undef HAVE_*` 互证。**打完补丁后的 usage 输出已实测**：消费者断言 T3 `--help prints upstream usage with resolved program name (rc=1)` 为 `PASS`（`reports/test-report.md:92`，汇总行 `MCDS_TEST_SUMMARY total=9 passed=9 failed=0`）⇒ 补丁后字符串面是一手读数，不是推断）。
- ✅ E248 **applied**：`apply_conandata_patches` 之后 `Makefile.am` 与 `Makefile.in` 的 mtime 先后会触发 automake 重生成崩溃 ⇒ 本包 `build()` 以 `autoreconf -fi` 显式自举（一手：构建树日志 `RUN: autoreconf -fi`）。
- ✅ E490 **n/a**：该条处方是恢复 autotools 辅助脚本执行位，而本包解包树里根本没有这些脚本载体（`reports/upstream-test-scan.txt` 的 [02] 段 47 条枚举内无任何 `build-aux/`、无 `configure`（[02] 段第 10 条 `./configure.ac` 是 autoconf 输入，不是 E490 处方要 `chmod +x` 的那类脚本），全部脚本由 `autoreconf -fi` 现场生成 ⇒ 属真不适用，判定理由详见「收口披露」节第 1 条。
- ✅ E074 **consulted**（FIFO/SELinux）：本包构建期未创建命名管道，也未因此调整并行策略 ⇒ 仅作为 make jobserver 风险的排除依据，未产生本包侧新读数。
- ✅ E114 **consulted**（HMDFS 上 `mktemp -d` 目录权限）：本包未走 `mktemp` 建临时目录的路径，未产生新读数。
- ✅ E011 **consulted**（HMDFS UID 映射与 `umask 077`）：本包未依赖该行为，未产生新读数。
- ✅ E337 **已摘除（原判误挂）**：该条讲的是 ACF 纯 Lua 模块运行时依赖 `acf-core`，与 mcds（C 语言 CardDAV 命令行同步工具）无关，本包全程没有它任一判据的读数 ⇒ 收口窗（主理-74）判定它是前任从别包模板带过来的残留，已把它从版本级 `manifest.yaml` 的 `knowledge_ref` 摘除（现 6 条：`E074/E114/E248/E203/E011/E490`），并已在 `knowledge_gained` 里补上 `E490` 的同行 ref 标记。唯一残留引用是 `conanfile.py:19` 的一行注释（写着 `知识 E337`）：它属导出件，改一字节就换 recipe revision ⇒ 本窗不动它，**以本行为准**。W4 r2 独立复核已确认摘除成立。

- ✅ [导出件里两处文字不精确，本窗故意不改并给出依据] r2 的 P2-1 半闭项：真实函数名是 `main.c` 的 `program_name()`（一手：`patches/0001-src-main.c-progname-fallback.patch` 的 hunk 头、以及本 notes 「遇到的问题与解决方案」表第 5 行与「源码修改」节的引用），而 `conandata.yml:22` 的 `patch_description` 把它写成了 `get_progname()` ⇒ 属描述文字误写，不改变补丁行为与构建语义。上一窗曾把「conanfile.py 的注释里也有一处 progname 误名」写进本行：**该说法不成立**，实测 `grep -c progname conanfile.py` = 0，`conanfile.py` 内唯一的文字不精确是 `layout()` 注释里的早期路径（见「收口披露」节第 4 条）。不改的理由与 `conanfile.py` 同源：`conandata.yml` 的 `patches:` 段参与 recipe revision 计算，改一字节即换 RREV ⇒ W3 判决（`reports/conan-create.log`，27231 B，`sha256 715122e8fefdfda91762728f7b1bf208eaf6ced814d20b5682f72054fe84e2e3`）与全部行号锚作废、还要全量重审。本窗已把整改棒先前对 `conandata.yml` 的那处文字改动**回退到原字节**（提交 `8b27962a22`，用 `git show b249942b5c:...conandata.yml > ...` 重定向还原，非 checkout/restore），实测 `git diff --name-only b249942b5c..HEAD -- conandata.yml conanfile.py patches` 为空 ⇒ 导出面与 W3 取证时逐字节相同，无需重跑 `conan create`。


---

## 收尾块（收口窗主理-74 于 2026-09-27 手写转写，依据 = 盘上既有判决件）

⚠ 本窗**未重跑** `finish`/`conan-verify`：重跑会覆盖 `reports/w3-local-ci.log` 与 `conan-create.log`，
使下面引用的行号与哈希锚集体作废（既有口径）。以下每行读数都注明载体。

- 路径：A（autotools 自举），1 条 portability 补丁，无源码逻辑改写
- 依赖：`curl/8.15.0` + `libxml2/2.15.3`；`tool_requires` = `automake/1.18`、`libtool/2.5.4`、`gettext/0.22.5.1`
- 上游测试：**0 个**（`find . -type f | wc -l` = 47，树内无 `tests/`、`Makefile.am` 无 `TESTS`/`check_PROGRAMS`）⇒ ⛔ 不得写"上游测试全通过"
- `conan create`：**通过**（B 机，`Building from source` + `Calling build()` + 22 行真实 clang 编译）
- `conan-verify`：**PASS**（G0/G1/G2/G3/G4 + L2/L4/L5 全 ✅，载体 `reports/conan-verify-report.md`）
- 消费者测试：**9 通过 / 0 失败 / 0 跳过**（T1 T1b T2 T2b T3 T4 T5a T5b T6；`MCDS_TEST_SUMMARY total=9 passed=9 failed=0`）
- 货源：`https://github.com/t-brown/mcds/archive/0e150e90439bac5b306f5ca17091db4a300b76b2.tar.gz`，
  sha256 `4144bfbb2735860ea2c759a03d2f2b18bc5c4b79d40d24b95a91694c4b29e986`（B 机 curl 实算 + Windows 侧独立下载各测一次）
- 未复证项：CI 流水线与 AI 审查（本窗不建 PR、不触发 CI）、跨机（A 机）构建
- 知识面：`knowledge_ref` 6 条（`E074/E114/E248/E203/E011/E490`）逐条交代于「发现与知识」节；`knowledge_gained` 每条带同行 `knowledge_ref` 标记。
  `check_knowledge_gap` 在 W4 r2 整改后复跑读数（本窗与 r3 审计棒各独立跑一次，两读一致）：`notes.md: total=8 extracted=8 pending=0 failed=0`、`manifest.yaml: knowledge_count=9 unreferenced=0`、`✅ 知识完整性检查通过`。

**编译结束**: 2026-09-26 10:49（`reports/conan-create.log` mtime，即 W3 取证时刻）
**最终状态**: built（W4 r2 后待 r3 复审；本窗不改导出件，故 RREV 与上列判决件保持绑定）
