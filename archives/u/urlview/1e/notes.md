# urlview 1e 适配笔记（z74-urlview / B 机 / 主理-74）

任务号 11553，档位【易】。构建机 = B 机，worktree `~/qzy/主理-74-urlview-1e`，分支 `feat/urlview-1e`，
基线 `48d9cee6844d0fca1f25e86c2df1293b904855d8`，`CONAN_HOME=~/tmp/ch/home-urlview`。

---

## 1. 定源（第一关，一手）

Debian 池件与上游产物**逐字节同一文件**，官方址已实证可用：

| 址 | http | size | sha256 |
|---|---|---|---|
| `https://deb.debian.org/debian/pool/main/u/urlview/urlview_1e.orig.tar.gz` | 200 | 31192 | `8522c5a560def04a022faad66a1b4be5c895ecab9a93dc63c49969febcc8d571` |
| **`https://git.sr.ht/~nabijaczleweli/urlview-ng/archive/1e.tar.gz`**（conandata 采用） | 200 | 31192 | 同上（**逐字相等**） |

- 官方址二次独立下载同 sha256（确定性成立），内层前缀 `urlview-ng-1e/` ⇒ `strip_root=True` 可用。
- 实物身份：解包 README 首行即 `urlview-ng / https://git.sr.ht/~nabijaczleweli/urlview-ng`，
  并自述 "A new urlview upstream, originally derived from snapshot.d.o (0.7, 0.9), with imported
  patches from 0.9-24"。⇒ **`1e` 是 urlview-ng 的 SNV 版本**，Debian 只是把源包名沿用为 `urlview`
  （所以池路径在 `main/u/urlview/`）。登记表里那条"上游主页 sr.ht/urlview-ng"是**对的**，
  不存在"经典 urlview 与 ng 版混填"的问题；sr.ht refs 页可见 tag `0.7 0.9 1 1a 1b 1c 1d 1e`。
- 池件 dsc（`urlview_1e-1.dsc`，http 200 / 2156B）佐证：`Homepage: https://sr.ht/~nabijaczleweli/urlview-ng`、
  `Maintainer: наб <nabijaczleweli@nabijaczleweli.xyz>`（**上游作者本人打包进 Debian**）、
  `Checksums-Sha256` 列同一 sha256；池内另有 `urlview_1e.orig.tar.gz.asc`（833B，
  sha256 `f918f4f46a52ee0538022dc8f6a127c20beccf259be5f248f5b25e5e311063ab`）= 上游对 .orig 的 PGP 签名
  ⇒ .orig 非 Debian 重打包。
- 版本串按任务原文 `1e` 使用，未做任何"归一化"。

## 2. W0 依赖（精确探针，不用通配 conan list）

| 引用 | 命令 | 读数 |
|---|---|---|
| `ncurses/6.5` | `conan download ncurses/6.5 -r=ohpcd --only-recipe` | rc=0 → 配方已发布 |
| `ncurses/6.5` | `conan install --requires=ncurses/6.5 --build=never -pr:h/-pr:b=ci/conan/profiles/ohos-aarch64` | **rc=0**，日志 `Package installed 21b17f8b2bc0…` ⇒ **本平台二进制可得**（R35 口径） |
| `ncurses/6.6` | `conan download --only-recipe` | rc=0（本包取 6.5，与上游 Build-Depends 的宽松面一致） |
| `ncursesw/6.5` | 同上 | rc=1（制品仓无此引用） |
| `libintl/0.21`、`gettext/0.21` | 同上 | rc=1（无此引用；`gettext/0.22.5.1` 才是 rc=0） |

`preflight_check.sh urlview/1e` 首轮：`[OK] 预检通过（无依赖需要检查）`（那时 conanfile 尚未生成，属正常）。
R36：唯一依赖 `ncurses/6.5` 已发布 ⇒ 无未发布依赖、无需 `$P block`。

## 3. 构建系统实物形态与关键决策

上游是**裸 GNU Makefile**（20 行核心 + `$(shell …)` 探测），不是 autotools：无 configure/configure.ac。
`.build-context` 里 `BUILD_SYSTEM="autotools"` 是探测误判（实物 `Makefile` 是唯一入口，
`check/install/clean` 均为手写目标）——配方按 makefile 走，未据该字段生成任何 autotools 步骤。

| 决策 | 依据（一手读数） |
|---|---|
| `CC`/`CXX` 由 `tools.build:compiler_executables` 注入 | 上游默认 `CC ?= cc`、`CXX ?= c++`；本机实测 `cc MISSING`、`c++ MISSING`，只有 `/data/service/hnp/bin/{clang,clang++}`。不注入时第一条 make 就 `No such file or directory`（rc=127 实测）。R33 一致。 |
| 依赖旗标走**环境**通道，不走 make 命令行 | 上游 `CPPFLAGS += -DVERSION=… -DDEFAULT_REGEXP=…`。命令行传 CPPFLAGS 会整段覆盖 `+=`：实测丢掉 `-DVERSION` 后 `urlview.c:519` 的 `sizeof(BRAND)` 变语法错误（`error: expected ')'`，7 errors）。 |
| `CURSESCONF='echo #'` 钉死 | 上游 `ADD_L := $(shell $(CURSESCONF) --cflags)`、`LDLIBS += $(shell $(CURSESCONF) --libs 2>/dev/null \|\| echo -lncursesw)`。默认值 `ncursesw6-config` 在本机会命中宿主副本 `~/.harmonybrew/bin/ncursesw6-config`（实测存在）⇒ 宿主前缀混入、W3 与 CI 产物不一致。取 `echo #` 后两个探测都返空，库全由 conan 的 LDFLAGS 给。上游注释本身就给了这种写法。 |
| `VERSION=1e` 必传 | 上游 `VERSION ?= $(shell git describe)`，发行包无 `.git`：实测 make 输出 `fatal: not a git repository (or any parent up to mount point /storage/Users)`，版本会被编成空串。`SOURCE_DATE_EPOCH=0` 同理（手册页日期取自 `git log`），且这正是上游自己 `.builds/sid+void.yml` 的离线包做法。 |
| `SHELLCHECK=:` | 上游 `.builds/sid+void.yml` 在 void 分支里用的就是 `make check SHELLCHECK=:`；本机 `shellcheck MISSING`（实测）。 |
| `LOCALES=`（不出 .mo） | 上游 `LOCALES := $(wildcard *.po)` 仅在 `command -v msgfmt` 成立时赋值 ⇒ 产物随构建机有无 msgfmt 而变（本机 `/data/service/hnp/bin/msgfmt` 存在，CI 不确定）。命令行赋空覆盖 `:=`。等价 Debian 自己的 `gettext <!pkg.urlview.noloc>` 档；随包也无 .mo，运行期 locale 前缀问题一并消掉。 |
| `PREFIX=`（空）+ `DESTDIR=<package_folder>` | 上游默认 `PREFIX ?= /usr/local`、`SYSTEM_INITFILE ?= /etc/urlview.conf`。留空前缀 + DESTDIR 使产物落 `<pkg>/bin`、`<pkg>/share/man/man1`、`<pkg>/etc`，不把任何主机绝对前缀编进二进制（R49 / PF6）。 |
| 三条 make 钉 `cwd=self.source_folder` | 首跑 `conan create` 实测 `make: *** No rule to make target 'all'. Stop.`——默认 cwd 是 `build-release` 子目录，裸 Makefile 只存在于源码目录。与同仓 `archives/m/mpgtx/1.3.1/conanfile.py` 的 `cwd=self.source_folder` 范式一致。 |
| `-j1` | R9。 |

## 4. OHOS 侧读数 ↔ 既有知识条目（逐条对原文 root_cause 判，不看标题）

| # | 本包一手症状 | 检索（命令 + 命中数，库=`knowledge/graph/*.kv`，542 条） | 判定 |
|---|---|---|---|
| 1 | sysroot `…/sysroot/usr/include/libintl.h` 存在但**只有宏、零函数声明**；`clang -fsyntax-only` 包含它 rc=0，而调用 `gettext()` 报 `call to undeclared function 'gettext'`；sysroot 下 `find … -name 'libintl*'` 只有该头，**没有任何 libintl 库**，`-lintl` 链接仍失败 | `grep -ril "__has_include" *.kv` → **0**；`grep -rilE "stub header\|桩头\|空壳头"` → **0**；`grep -ril libintl` → 8 条，读最近者 E015 原文：其根因是"检测到 libintl.h 后用 dgettext 但没加 -lintl"，方案 `configure … LIBS="-lintl"` | **不 hit（相邻家族）**。E015 的前提是"系统里真装了 gettext、补 `-lintl` 即可"，本平台实测该前提不成立（桩头 + 无库），其 rec_command 在此不可执行。方向同源的是它的 fallback（--disable-nls 走 identity 宏） |
| 2 | `reallocarray`：`clang -D_GNU_SOURCE -Werror=implicit-function-declaration` → `error: call to undeclared function 'reallocarray'`；自行声明后链接仍 `>>> undefined symbol: reallocarray`；`llvm-nm -D --defined-only <sysroot>/…/libc.so \| grep -c reallocarray` → **0** | `grep -ril reallocarray *.kv` → 1（E368）；`grep -ril "call to undeclared function"` → 6（E032/E033/E152…） | **不 hit**。E368 原文根因是 Meson `--wrap` 故障注入测试的能力门（error_signature 为 `Checking for function .*reallocarray.*NO`），与"裸 Makefile 直接调用 + libc 根本没这个符号"不同因；E032/E033/E152 是 musl **宏门控**（符号在、声明被 `_GNU_SOURCE`/`_XOPEN_SOURCE_EXTENDED` 挡），本例是**符号确实不存在**，补宏无解 |
| 3 | ncurses 头/库不在默认搜索面：`clang -fsyntax-only` 含 `<ncurses.h>` → `fatal error: 'ncurses.h' file not found`；默认 include 搜索只有 clang 15 内置 + sysroot 两项 ⇒ 必须走依赖 | `grep -ril "ncurses.h" *.kv` → **0**；SKILL §7 Gotchas 已有"ncurses 共享库须 `--without-shared`"条目 | **不 hit（症状面）**。依赖 `archives/n/ncurses/6.5` 本身即 OHOS 侧已沉淀做法：该配方 `configure()` 在 OHOS 上拒 shared、`cpp_info.libs=[ncursesw,panelw,menuw,formw]` 全静态 |
| 4 | `-std=c++2b` + `std::bit_width(unsigned)` + `0z` 字面量 + `accumulate(…,0z,…)` 在 clang 15.0.4 / SDK 26.0.0.18 上**全部可用**（三条 `clang++ -std=c++2b -fsyntax-only` 各 rc=0） | 同族旧底稿 `archives/u/urlview-ng/1e/notes.md` 记 #6"std::bit_width C++23 不支持→换常量"、#7"`0z` 不支持→换 0UL" | **推翻旧结论（R15 不盲从）**：那两条在本 SDK 上不成立，本次不打任何 C++23 补丁即通过。旧底稿大概率是 `-std` 被 profile 的 `compiler.cppstd=17` 拖住所致（profile 实测 `compiler.cppstd=17`；上游 CXXFLAGS 末尾自带 `-std=c++2b`，后出现者胜 ⇒ 本配方不再传 `-std`） |
| 5 | `tcgetattr/tcsetattr` 系（dokey.c/enter.cpp 的 termios 面）编译无障碍；本包**没有**跑到 `tcflush/tcdrain/tcflow`，且 test_package 全程走 `!isatty(1)` 抽取分支，不碰 `/dev/tty` | 与别的窗一手实测的"pty 两侧 tcflush/tcdrain/tcflow 一律 EPERM"面一致，本包**未触发**该面 | 不适用（未触发），仅登记以免后来者误以为本包验证过它 |
| 6 | `url_handler.sh` 首行 `#!/bin/sh` | 与 OHOS"无 FHS 解释器（`/bin/bash`、`/usr/bin/python3` MISSING，只有 `/bin/sh`=toybox ash；`#!/usr/bin/env` 可用)"一致 | **hit（既有能力面）**：上游脚本本身就是 `#!/bin/sh`，与 ash 兼容；test_package 里对该 shebang 做了钉死断言，装成 `#!/bin/bash` 会被抓 |
| 7 | `/tmp` 只读：`> /tmp/d.txt` 报 `sh: can't create /tmp/d.txt: Read-only file system` | SKILL §7 / E002 | **hit**：全程用 `$TMPDIR=~/tmp/uc2/z74-urlview/tmp` |
| 8 | HMDFS 无执行位：`scp` 落地的脚本一律 `660`，`shutil.which()` 不认 ⇒ 不能用"往 PATH 里塞可执行垫片"绕框架探针 | SKILL §7"HMDFS 软链接/chmod 不生效"+ R49 ②（`os.access(X_OK)` 恒 False） | **hit**：改用导入级旁路（见 §5），不在盘上伪装可执行文件 |

## 5. 工具链缺陷（当场遇到、本窗未改框架）

- **`scripts/ohc/check_env.py:31-33` 有 NameError**：`except Exception: return False, str(e)` 里 `e` 未绑定。
  触发条件实测：本机 `~/usr/local/bin/automake` 的 shebang 是 `#!/storage/Users/currentUser/usr/local/bin/perl`，
  而 `~/usr/local/bin/perl` **不存在**（`ls` 报 No such file）⇒ `subprocess.run` 抛 FileNotFoundError
  ⇒ 走到坏 except 分支 ⇒ `init-build` Step 8 整体崩（`ohc-run.py init-build urlview 1e` rc=1，栈顶即此处）。
- 本窗处置：写 `~/tmp/uc2/z74-urlview/init_build_driver.py`，在**内存里**把 `ohc.init_build.check_env`
  替换为 no-op 后调 `init_build_cli()`，其余 8 步走原码；不改 `scripts/`（框架改动须独立 PR，W2），
  也不在共享目录放任何伪装可执行的垫片。绕过后的 init-build 日志 rc=0。
- 正解留给主窗：`except Exception as e`（一行）。任何用 automake/autoconf 探针的包在这台机器上都会撞。
- 另记：`recipe-search urlview` 返回"无相似配方（语料 6173 条）"；`ohc-run.py` 的 R46 挂点在本机反复报
  `终态 result.json 已上报（draft:false），跳过里程碑草稿`——即 `~/ohpcd-ai-worker-result.json` 有**别的任务的终态残留**，
  本窗未动它（是别人资产），但主窗若要让 R46 生命周期草稿真正落盘，需先清该残留或给本任务设 `OHC_RESULT_OUT`。

## 6. 同族底稿对照（`archives/u/urlview-ng/1e`，status=built，2026-06-03）

不可当结论照搬，且它自身已不合规：
- `manifest.yaml` 里 `source.url` 写的是 `http://ftp.debian.org/debian/pool/…`（**http 明文 + 池址**，
  现 PF7 双违规），`sha256: ""` 空。
- 依赖写 `ncursesw/6.5` + `libintl/0.21` —— 本窗实测这两个引用**制品仓里都不存在**（rc=1），
  即该底稿的配方今天过不了 PF4/W0。
- 其 9 条"踩坑"里 #6/#7 被本窗实测推翻（见 §4 第 4 行）；#2 reallocarray 与本次方向一致但当年是
  直接改调用点为 `realloc(...)`（丢溢出检查），本次改为带溢出检查的 compat（OpenBSD 语义）。
- 无 `conanfile.py`/`conandata.yml`/`test_package/`（只有 manifest/notes/patches/reports）⇒ 从未进过 Conan 门禁。

## 7. 测试（R51 三步法）

### 7.1 上游测试清点（适配前）
- 无 `tests/` 目录、无 `CTestTestfile`/`add_test`、无 automake `TESTS`/`check_PROGRAMS`（裸 Makefile）。
- `Makefile` 的 `check` 目标全文只有两条命令：`$(SHELLCHECK) url_handler.sh` 与 `./quote`。
- `quote.cpp:56-63` 的 `#if TEST` `main()`：一张 2 行表，逐行 `assert(!std::strcmp(res, exp))`
  ⇒ **上游自动化断言 = 2 条**（quotesub 的 shell 转义）。shellcheck 是 lint 不是断言，本机 MISSING。
- `.builds/sid+void.yml` 的 `smoketest: urlview urlview-ng/text`（把上游自带样例 `text` 喂进去）。
- ⇒ 上游**没有**针对 urlview 主流程（正则抽取、菜单、handler 调用）的自动化用例，只有一条冒烟。
  本包如实申报上游断言数 2，**不写"上游测试全通过"**。

### 7.2 上游用例实际运行（本包在 W3 里真跑）
`conan create` 的 `build()` 里执行了上游自己的 `make check`（`SHELLCHECK=:` 形态）。
手工树同形态实测输出（rc=0）：
```
abc %s def %s    abc 'qwe'\''rt' def %s
ghi              ghi 'qwe'\''rt'
```
2 条断言均通过（assert 生效、未定义 NDEBUG）。

### 7.3 消费者测试（真运行，非"编译冒充运行"）
断言实装在 **`test_package/test.sh`**（POSIX sh，toybox ash 可跑），`test_package/conanfile.py`
只做驱动：`sh <test.sh> <pkg>/bin/urlview <pkg>`，在 `conanrun` env 下执行。
跑的是**包里的 `urlview` 二进制**，走 `urlview.c:425`
`if(getenv("URLVIEW_DEBUG") || !isatty(1))` 这条无头分支（只抽取、打 stdout、`return 0`），
不碰 `/dev/tty`、不开 curses 屏 ⇒ 构建机上可重复。

> 为什么实装在 `.sh` 而不是 `conanfile.py` 里：L0c 静态结构闸在
> `ci/conan/build_and_test.sh` 的 `find test_package -maxdepth 2 -name "*.<ext>" -not -name conanfile.py`
> 上，**显式排除 `conanfile.py`** ⇒ 只写在 conanfile 里的断言对 L0c 不可见（本包 09-27 首轮 CI 即
> 因此判 `no_test_sources`，详见 §12）。断言只此一份，⛔ Python/shell 两处各写一遍。

- 10 次真运行：8 个抽取用例 + 1 个 `urlview -`（stdin 形态）+ 1 个缺文件负例；
  每个用例断言"退出码 + stdout/stderr 逐字相等"。
- 期望值**不是照正则猜的**：先用同一台机器手编的 urlview 实测取回（`~/tmp/uc2/z74-urlview/cases.sh`），
  覆盖 6 种 scheme（http/https/ftp/gopher/gemini/mailto）、`www2.` 形态、同一行两 URL、
  句末点号裁剪、括号包裹右括号裁剪、无 URL 空输出。
- 另 5 条安装面断言：`bin/urlview`、`bin/url_handler.sh`、`share/man/man1/urlview.1`、
  `etc/urlview.conf` 存在 + `url_handler.sh` 首行必须 `#!/bin/sh`。
- 运行计数由 `test.sh` 自己打印（本轮 `conan create` 日志实测两行）：
  `urlview consumer assertions: 25` / `urlview consumer tests: PASS (25 assertions)`。
- 汇总：**PASS 25 / FAIL 0**（任一不符即 `test.sh` 以 rc=1 退出 ⇒ `self.run()` 抛 `ConanException`，日志无 PASS 行即为失败）。
- 负例语义按上游真实行为钉住（缺文件只 warn、整体仍 rc=0），不伪造成"应当失败"。

## 8. 补丁（2 个，均由 `refresh-patch --auto` 生成，非手写）

- `patches/0001-enter.h.patch`（+18/-0）：`reallocarray` compat，落在 C/C++ 共用的 `enter.h`
  （`urlview.c:393`、`enter.cpp:47/55` 三处调用点不动）。溢出检查按 OpenBSD 语义（`nm` 实测 libc 无该符号）。
- `patches/0002-urlview.c.patch`（+9/-2）：新增 `URLVIEW_NO_GETTEXT` 开关 + 用单点 `UV_USE_GETTEXT`
  让 `urlview.c:25` 与 `:187` 两处探针同进同退；不引入任何平台宏（PF5/R8 无 `__OHOS__`）。
- 两补丁在 `conan create` 干净树上的应用读数见 `reports/conan-create.log`（Apply patch ×2 后接 RUN 行）。

## 9. 待补 / 已知未尽

- 未生成 `.mo`（见 §3），因此运行期无本地化文案；如主窗判定必须带 fr/pl 目录，
  正解是 `requires gettext/0.22.5.1`（实测已发布，提供真 `libintl.h` 与 `-lintl`）并解决 TEXTDOMAIN 运行期路径，
  属功能扩展，未在本任务内自行扩范围。
- 菜单/handler 分支（`initscr()` 之后、`execl("/bin/sh", …)`）在 CI 与本机上都不具备可断言的非交互入口，
  未做真机交互验证；已验证的是抽取分支与安装面。
## 10. 判决摘要（机器可读，值由收口脚本从盘上重算；2026-09-27 23:10 L0c 整改复跑后刷新）

- W3 `.ci-result.json` 路径: `archives/u/urlview/1e/.ci-result.json`（被 .gitignore 覆盖，不入 PR，故抄录于此）
  - `step: W3_local_ci`
  - `exit_code: 0`
  - `timestamp: 2026-09-27T23:10:11.447276`
  - `log_sha256: fd2da51cf0b3946f448bfe02c2474865a38253fca132bd164ba9d7a60b7967f6`
  - `integrity_hash: 5b860df8c7ac3753`
  - 首轮（09-27 03:10，`log_sha256 55738f84…`/`integrity_hash 9174d1bb…`）已被本轮复跑覆盖；
    那一轮的 W3 绿是**假绿**（L0c 只在有 conan 生成 `.sh` 的 worktree 上成立），详见 §12。
- 交叉复核：`reports/w3-local-ci.log` 实测 sha256 = `fd2da51cf0b3946f448bfe02c2474865a38253fca132bd164ba9d7a60b7967f6`（与上面 log_sha256 一致）
- conanfile.py（配方）sha256 = `af7da4162ae0a91a13b8d43921ef920205c3e4dab34ce392607b4972cdb5c918`（本轮未改）
- `test_package/test.sh` sha256 = `9002cfd88e1307414c1c7be953a048ab4a6b22714f0b20712d9b682fbe6356c8`
- `test_package/conanfile.py` sha256 = `31ad042c34e5b13bba820fe38e5962ace30dfb96ae32e21352fdbb7ad854f56d`
- `test_package/MANIFEST.yml` sha256 = `50637a70f2a57090c3a73476f5137152364427bf5b4eca80a2f94474a390425a`
- 补丁 `0001-enter.h.patch` sha256 = `be8fbee0c2e3be94e80e5e30bcf0057af28d48df2b8916cfe716caf0f2bfab7d`
- 补丁 `0002-urlview.c.patch` sha256 = `f67c5618f10275d2634c77f1c79926f47fd406e8153cd0ac7ad3b118c72f7a9a`
  （本轮 `refresh-patch --auto` 重新生成的这两枚与上面两行**逐字节同一**，`git hash-object` 亦等于 HEAD 的 blob）
- 门禁读数（2026-09-27 23:0x 复跑）：`preflight_check.sh` ✅（ncurses/6.5 已发布、版本未占用）；
  `recipe-search urlview` ✅（top1 = 本包骨架）；`conan-verify` **G1 PASS / G2 PASS / G3 PASS**（rc=0）；
  W3 本地 CI 模拟 ✅（`✅ W3 本地 CI 模拟通过`）；`graph validate` ✅（`All checks passed (169 warnings)`，rc=0）；
  `ohc-run.py build` ❌ rc=2 —— 与本包改动无关的工具链探针缺陷，证据见 §12.3。
- W2：本 PR 仍只含 `archives/u/urlview/1e/**`（11 文件，新增 `test_package/test.sh`），无框架文件。
- JC 口径说明：`ci/scripts/junk_check.sh` 在无 `pr.diff` 时退回 **full 模式（git ls-files 整仓扫描）**，本基线上会被 3 枚**已合入 main 的他包隐藏件**判失败（`archives/c/cloog/0.21.1/.build-closed`、`archives/c/cloog/0.21.1/.staging-verified`、`archives/k/kics/2.1.20/.staging-verified`，实测 `git ls-files --error-unmatch` 三者均 TRACKED，其中一枚由 `906cc59ae7`（cloog 0.21.1，2026-09-11）带入）。本包按 CI 真实口径生成 `pr.diff` 后以 prdiff 模式复扫，`Junk Files: 0` 通过；那 3 枚属他人已入库资产，本窗不删不改，交主窗定夺。
- 补丁平台宏自查（PF5/R8）：两补丁新增行内 `__OHOS__` 计数 0（见下条 grep 口径），故按可移植改动登记，不声明 platform_only、不写 guard 宏。


## 11. 发现与知识（W4 r1 后由收口窗定稿：逐条 ref 与判定依据）

- ✅ **libintl 空壳头骗过 include 探针** → `DRAFT-13410-trueprint-libintl-stub-header`（同族另有 `DRAFT-latino-1.4.4-musl-empty-libintl-bison-dgettext` 与 `knowledge/drafts/E2181-draft-1531`）：本包一手症状是 sysroot 的 `libintl.h` 只 `#define __USE_GNU_GETTEXT`、零函数声明（`#include` 本身 rc=0，调用 `gettext` 才报 `call to undeclared function`），与该草稿 `error_signature` 的 `implicit declaration of function \'gettext\'` 同形 ⇒ 判 **hit**。⚠ 更正一条执行棒的取证面：它原先只扫 `knowledge/graph/*.kv`（0 命中即写"无人沉淀"），漏扫 `knowledge/drafts/` ⇒ 那个 0 命中**不足以支撑 create**，已由 W4 r1 的宽检索纠正。`E015` 复核后仍不等同一条（其 `root_cause` 前提是"系统里装有 gettext/libintl、只缺 `-lintl`"，本包 sysroot 内根本没有 libintl 库；本机 `~/.harmonybrew` 另有一份 `libintl.h` + `libintl.so.8`，属**另一前缀**、不参与 conan 的 sysroot 检索）。
- ✅ **libc 不提供 `reallocarray`（声明与符号双双没有）** → `DRAFT-ohos-musl-glibc-specific-symbols`：其处方"提供无条件替代实现、⛔ 平台宏"与本包 `patches/0001-enter.h.patch` 的做法同一条（该补丁在 `enter.h` 内加 `static inline void *uv_reallocarray(...)`，带 `SIZE_MAX / size` 溢出检查，C 与 C++ 两个单元共用）。成品先例两处一手可见：`archives/c/confuse/3.3/notes.md:107,112,115`（编译自带 `reallocarray.c`）与 `archives/b/bmon/4.0/conanfile.py:46,47,129`（`_GNU_SOURCE` 与自带实现的取舍）。⚠ 该草稿的 `error_signature` 是**枚举式样本清单**（字面不含 reallocarray），但其 `title`/`affected_scope` 明示覆盖"musl 缺 glibc 特有符号"整族 ⇒ 按"字面命中≠症状同形、组合型知识不判重"的口径归入该条，判 **hit**。
- ✅ **裸 Makefile 的变量传递三层** → 第 1、3 层直接落在 `E392`（其 `title` 三项即 `get()` 显式传 filename 避免 BadZipFile / `tools.build:compiler_executables` 用 `check_type=dict` 整体取 / make 默认 cwd）⇒ **hit**；第 2 层"make 命令行赋值会**覆盖**而非追加上游 `CPPFLAGS += -DVERSION=...`，实测导致 `urlview.c:519 sizeof(BRAND)` 语法错"最接近的既有条目是 `DRAFT-hoedown-3.0.7-makefile-cflags-override` 与 `DRAFT-smemstat-0.02.13-make-cli-cflags-override`（同一"命令行变量与上游赋值互踩"机制族）⇒ 判 **hit**，⛔ 再开新条目造成家族撞车。
- ✅ **C++23 面（`-std=c++2b`、`std::bit_width`、`0z` 字面量）在 clang 15.0.4 + SDK 26.0.0.18 实测全绿** ⇒ **不是新机制**，属对同族归档 `archives/u/urlview-ng/1e/notes.md:28,29,44,45` 的**纠正**（该处第 6 条把 `std::bit_width` 归为 C++23，实为 C++20；两条断言的载体也不是严格互斥关系）。本窗不改他人归档，只在本包留一手读数并在此声明。
- ✅ **综合判定 `B判定=hit`** ⇒ 本 PR **不携带** `knowledge/drafts/` 成对件、**不建**知识库扩展 Issue、标题**不用**【知识库扩展】前缀（四个候选全部命中既有沉淀，无一未覆盖）。
- ✅ **交付物缺三件的结构原因**（非本包遗漏、非缩分母）：`reports/` 与 `packaging/` 被仓根 `.gitignore` 通配排除（对照已合入的 `archives/m/mpgtx/1.3.1` 同样没有这三件）；建 `packaging/` 制品会撞 PF2 ⇒ 本包不造伪制品。
- ✅ **W4 r1 判 `pass`（P0=0 P1=0 P2=3 P3=4）**，绑定 HEAD `65bdf7f9a63e32d2500f76f0d17c6665349487c7`；其三条 P2 的处置：`manifest.yaml:13` 的 `{software}` 占位已回填 `urlview`、`:68` 的 `patches_applied: []` 已按 `patches/` 实物补两条（并与 `patch_classification` 一致）、本节的检索更正即为第三条；两枚 `.patch-backup-*` 与 `test_package/` 下 conan 生成的 `.sh` 已移出 worktree 至 `~/tmp/uc2/z74-urlview/relocated/`（⛔ 只靠 ignore 兜住）。

## 12. 09-27 平台 CI L0c 失败归因与整改（收尾-1 子代理棒，B 机）

### 12.1 一手事实
- 平台 CI 判决 `2026-09-27T03:38:04+08:00`：`## CI 校验失败`，第一条真实错误逐字
  `[fail] L0c: No test source files in test_package/` ⇒ `urlview/1e — L0 quality gate failed: no_test_sources`，
  随后 L1/L2/L4/L5 全 `skip: blocked_by_L0`，exit 1。
- L0c 实装判据（本 worktree `ci/conan/build_and_test.sh` 第 345-358 行，本轮 `sed` 复核原文）：
  对 `test_package/` 用 `find -maxdepth 2 -name "*.$ext" -not -name "conanfile.py" -print -quit`
  按 `c cpp cc cxx sh py` 依次找，任取到 1 个即通过 ⇒ **`conanfile.py` 被显式排除在外**。
- 入库集取证：`git ls-files archives/u/urlview/1e/test_package/` 整改前只有 `MANIFEST.yml` + `conanfile.py`
  （与 `GitCode pulls/13078/files` 回读同结论）⇒ 平台侧确实一枚测试源文件都没有。

### 12.2 根因：本地那轮 W3 的 L0 绿是**假绿**
- §11 末条的收口动作把 `test_package/` 下 conan 生成的 `conanrun.sh / conanbuild.sh /
  conanrunenv-*.sh / deactivate_*.sh`（现存 `~/tmp/uc2/z74-urlview/relocated/`，实测就这 7 件 + 两枚
  `.patch-backup-*`）**当成杂件移出了 worktree** —— 而 03:10 那一轮 L0c 的 `find` 抓到的正是它们，
  于是本地 `reports/w3-local-ci.log` 印 `[ok] L0: All quality gate checks passed`，平台看到的却是空集。
  移出动作本身没错（那些是生成物、不是测试件）；**真正的缺口是本包从来没有一枚入库的测试源文件**。
- 复算取证：把 `git archive HEAD` 的**提交态**解到 worktree 之外、逐字套 L0c 那段 find
  （驱动脚本 `~/tmp/uc2/z74-urlview/l0c-replay.sh`）⇒ 整改前（HEAD=`423a1c3550`）
  `[fail] L0c: No test source files in test_package/`，整改后
  `[ok] L0c: test source found -> archives/u/urlview/1e/test_package/test.sh`。

### 12.3 整改与三处工具链坑（本棒不动 `scripts/`，留主窗）
- 整改：新增 `test_package/test.sh` —— §7.3 那 25 条断言的 shell 实现，**断言只此一份**（⛔ Python/shell 双写）；
  `test_package/conanfile.py::test()` 改为按同仓 `archives/u/uglify/3.19.3` 的范式驱动它
  （`sh test.sh <pkg>/bin/urlview <pkg>`，`cwd=self.source_folder`、`env="conanrun"`）；
  `test_package/MANIFEST.yml` 的 `test_package_tests` 同步列两件（`.sh` = 断言载体，`conanfile.py` = 驱动）。
  夹具目录：`mktemp -d`（读 TMPDIR）→ 不可用时退回 `$HOME/tmp` → 两者都没有就 rc=3 红牌退出，
  ⛔ 静默把夹具写进 `archives/`（设备 `/tmp` 只读，见 §4 第 7 行）。
- ⚠ 坑 A（框架）：`ohc-run.py build` 的 pre-scan "make install 产物探测" 对**裸 Makefile** 包必然假失败 ——
  它先 `make install-binPROGRAMS`（实测 `make: *** No rule to make target 'install-binPROGRAMS'. Stop.`），
  随后自己的 `cp` 已把产物装进 `<staging>/usr/local/...`，探测却去看
  `<staging>/storage/Users/currentUser/usr/local/...` ⇒ 判 `❌ 安装无产物`、该步 rc=2。
  两次复跑（第二次沿用上一棒 `run-verify.sh` 的完整 env）**同一处、同一读数** ⇒ 与本包改动无关；
  证据 `~/tmp/uc2/z74-urlview/l0c-r2/{build.log,build2.log}`。本包构建真凭据是 `conan-verify` 的 G2
  （干净 `conan create`）+ W3，不以该探针为准。
- ⚠ 坑 B（框架，别在已收口的包上跑 `ohc-run.py build`）：坑 A 那两次探针 make **没传 `LOCALES=`**
  ⇒ 上游 Makefile 自己跑了 `xgettext + msgmerge -Uiq fr.po pl.po`，改动了 `.work` 树的两枚 `.po`；
  随后的 `finish` 里 `refresh-patch --auto` 拿脏 `.work` 与 `.orig` 对比，多生出
  `0002-fr.po.patch`/`0003-pl.po.patch`（各 +23/-21，纯 msgmerge 行号重排），并把 `urlview.c` 那枚挤成
  `0004-urlview.c.patch`，而 `conandata.yml` 仍指向 `0002-urlview.c.patch` ⇒ W3 在 `export_sources()`
  直接炸 `ConanException: Patch file does not exist`（首轮 finish rc=2 即此，日志 `l0c-r2/finish.log`）。
  处置：`.work` 的 `fr.po`/`pl.po` 从 `.orig` 复原 → 归档回退 HEAD → 重跑 `finish` ⇒
  `refresh-patch` 重新生成的 0001/0002 与原 blob **逐字节同一**（`git hash-object` 相等，§10 的 sha256 亦相等）。
- ⚠ 坑 C（框架）：`finish`/`refresh-patch` 会把 `manifest.yaml` 的 `patch_classification` 从人工判定的
  `type: portability / platform_only: False / guard: none` **覆盖成** `type: auto / platform_only: True /
  guard: 'pending'` —— 与 §10 的 PF5/R8 自查（两补丁新增行 `__OHOS__` 计数 0）直接矛盾，
  也把 W4 r1 已收口的那条 P2 打回原形 ⇒ 本棒把 `manifest.yaml` 回退到 HEAD，只保留 W3/verify 的绿判据。

### 12.4 测试账本（五维，全部本轮实测同源）
| 维度 | 上游（urlview-ng 1e 自带） | 消费者（本包 test_package） |
|---|---|---|
| 静态总数 | `Makefile:44-46` 的 `check:` 只有 2 条命令：`$(SHELLCHECK) url_handler.sh`（lint，0 断言）+ `./quote`（`quote.cpp:55-63` `#if TEST` 表 2 行 × `assert` ⇒ **2 条断言**）；另 `.builds/{freebsd,openbsd,sid}.yml` 各写 1 条同一形态的 `smoketest: urlview urlview-ng/text` ⇒ **自动化用例 3 项 = 断言 2 + 冒烟 1，另有 1 个 lint 步** | 25 条断言（10 次真运行 × 2 + 安装面 4 + shebang 1） |
| 可执行数 | 3（`./quote` 的 2 条 + 冒烟 1 条） | 25 |
| 实测通过 | 3 —— `conan create` 内 `RUN: make -j1 … check` rc=0 并打印两条表行（`.ci_logs/conan_build_urlview_1e.log:105,109-110`）；冒烟形态用**本轮 W3 产出的包内二进制**在 `.work/text` 上复现：`env HOME=<空目录> <pkg>/bin/urlview text` ⇒ rc=0、stdout 21 行 URL（`~/tmp/uc2/z74-urlview/l0c-r2/smoke.out`） | 25（`consumer tests: PASS (25 assertions)`，同日志 :164-165） |
| 跳过 | 1（shellcheck lint：本机 `shellcheck MISSING`，按上游 `.builds/sid+void.yml` 同形态 `SHELLCHECK=:` 置空。`.mo`/gettext 面按 §3 的 `LOCALES=` 关掉，不计入分母） | 0 |
| 失败 | 0 | 0 |

- **未做（如实登记）**：上游那条冒烟**没有**钉进 `test_package/test.sh` —— 钉它需要把 `text` 与它的 21 行期望
  做成字节一致的夹具，本棒不肯手抄 40 行 UTF-8/IDN 文本再赌 byte-exact（手抄失真 = 假测试）。
  正解留给后续棒：以**原样文件**落地 `test_package/text.in` + `text.exp`（仓内有先例：
  `archives/a/abcmidi/20260609/test_package/sample.abc`、`archives/a/abook/0.6.1/test_package/test_input.csv`），
  然后 `cmp` 逐字节比。
- **未做**：菜单/handler 交互分支验证（§9 已记）；W4 独立审计未复审（`reports/audit-result.json`
  仍绑 HEAD `65bdf7f9a6`，本轮新增的 `test_package/` 三件需 W4 r2 覆盖）。
---

**编译结束**: 2026-09-27 23:54
**最终状态**: built
