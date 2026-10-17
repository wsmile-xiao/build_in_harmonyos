# anacron 2.3 适配笔记

## 编译环境
- 构建系统: makefile（上游**手写** `Makefile`，无 configure 脚本、非 autotools、非 cmake）
- 编译日期: 2026-10-06
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`，取自 profile `tools.build:compiler_executables`）
- 平台: HarmonyOS PC aarch64（HongMeng Kernel 1.12.0，musl libc）
- 状态: built

## 上游与源

| 项 | 读数 |
|---|---|
| 源 URL | `http://deb.debian.org/debian/pool/main/a/anacron/anacron_2.3.orig.tar.gz` |
| HTTP | 200 |
| size | 24085 B |
| sha256 | `ceee7520bc49f861499f7eff4c7990d21d39d8a1d3e24449947a7ed5aa34761d` |
| 顶层目录 | `anacron-2.3/`，18 个条目 |
| 构建件 | 1 个：`Makefile`（`distfiles`/`.PHONY` 齐全，无 configure） |
| 归档条目数（`tar tzf` 实测） | **18 = 1 个目录条目 + 17 个文件**（W4 P3-2 更正：此前写「19 个文件」是把 vendor/追踪文件摊平后的口径，非 tarball 实测） |

anacron 2.3 是 2000 年的上游最后一个 tarball；此后项目转由 Debian 维护，官方发布物只在 Debian pool，故源 URL 是 Debian pool（**PF7 会因此命中**，属已裁定例外）。

### 本地 preflight 的两条已知触发（W4 P3-1 补披露）

| 闸 | 判据 | 本包是否命中 | 处置 |
|---|---|---|---|
| **PF7** 源 URL 闸 | 明文 `http://` + Debian 重打包源 | **命中**（Debian pool 必触发） | 正文 `## 补充说明` 双披露（例外理由 + 逃生口出处 `preflight.py:39`）+ `--no-preflight`（**preflight 侧开关，⛔ 不是 `create-pr` 参数**） |
| **PF9** 分支/路径闸 | `check_branch_and_paths()` 判 `len(f.split("/")) < 5` ⇒ `archives/<l>/<pkg>/` 下**软件级**文件一律报「变更路径缺版本目录层」 | **命中**（被点名 = `archives/a/anacron/commands.json`；前一轮的软件级 `README.md` 已按 2026-10-06 裁决回退删除，见下方另注） | 与 **PF8「CLI 包必须有 commands.json」互斥**，属**既有工具假阳性**（依据 `经验库/12d §12.82`：已合并 vamps 0.99.2 `ec60ece1de`、pforth 2.0.1 `4a17d82bbb` 各带 3 个软件级文件正常合入，CI 侧 L0n/JC 不拦）。处置 = `run_preflight(repo,"upstream/main","HEAD")` 确认 PF1–PF8 + R52 全过、只剩 PF9 后走 `create-pr --skip-push --head <SHA>`，并 `OHC_PREFLIGHT=0` + 正文披露；**⛔ 不删 `commands.json`**（会转成 PF8/L0k 真失败） |

> 另注（2026-10-06 裁决回退）：`经验 §12.82` 同节明文「软件级 `README.md` **不是仓库惯例**、**为消 Step6 警告新增 README = 自己制造一条 PF9**」。
> 本包的 `archives/a/anacron/README.md` 是前一轮为消 Step6 警告所建，已按裁决 **`git rm` 回退删除**（交付物与规则保持一致，不再留「一边有 README、一边说非惯例」的矛盾）。
> **回退后实测（`finish5.log:89-93`）**：`⚠️ 软件级缺失: README.md` + `⚠️ 缺少 release tar.gz` + `⚠️ finalize 完成，有 2 个缺失 + 1 个一致性问题` —— **与预期完全一致、非阻塞**，同一轮 `Step10 ✅✅ submit 就绪`、`G2 PASS`、`W3 ✅ 本地 CI 模拟通过`、`EXIT_REASON=finish_success`。
> 回退后果（均**非阻塞**）：① Step6 的 `软件级缺失: README.md` 警告已回来 —— 该缺项本就是 `finalize_archive.py` 的建议性检查、`FINISH_RC=2` 是警告码；② **PF9 仍然必触发**，因为 PF8 硬要求的 `commands.json` 无法删（删了会转成 PF8/L0k 真失败）—— 这正是「PF8 与 PF9 自相矛盾」的既有反馈档根因，删 README 只是少一个报点、少一处自己制造的问题。
> ⚠ **规则冲突备查**：`knowledge/ARCHIVE-SPEC.md:72` 写的是「#### README.md（**必须**）」，与 `§12.82`「非仓库惯例、为消 Step6 新增 README = 自己制造 PF9」**直接冲突**。
> 本包**按 `§12.82` 的实证口径取舍**（依据：已合并 vamps 0.99.2 / pforth 2.0.1 先例；W4 复核四个门禁脚本对 `README|软件级|release tar|debug tar` **零命中**，唯一命中 `finalize_archive.py:86-90` 的 `log_warn`，且 `finalize-archive RC=2` 是**警告码**）⇒ 审阅者若以 SPEC 原文质疑 README 缺失，**以此二处为据**。（该规则冲突已由主理另立反馈档，归口幕僚。）

## 编译步骤

上游无 configure，全部通过 make 变量注入（见 `conanfile.py::_make_vars`）：

```bash
make -j1 CC=<clang> CPPFLAGS=-I. PREFIX= \
  BINDIR=<package_folder>/bin MANDIR=<package_folder>/share/man \
  SPOOLDIR=<package_folder>/var/spool/anacron ANACRONTAB=<package_folder>/etc/anacrontab \
  INSTALL_DIR="mkdir -p" INSTALL_PROGRAM=cp INSTALL_DATA=cp

make install <同上变量>
```

- **`PREFIX` 必须留空**：上游 `installdirs` 拼的是 `$(PREFIX)$(SPOOLDIR)` —— 只有 PREFIX 为空、`SPOOLDIR` 为绝对路径时才不产生 `<pf><pf>/...` 双拼；
- 同时 `SPOOLDIR`/`ANACRONTAB` 又必须是绝对路径（它们以 `-D` 宏烧进二进制）⇒ 四个目录全部显式传，绕开上游的双拼假设；
- **`INSTALL_DIR/INSTALL_PROGRAM/INSTALL_DATA` 必须覆盖**：本平台没有 `install(1)`（coreutils 装成 `ginstall`），用 `mkdir -p`/`cp` 是 POSIX 可移植写法。

## 遇到的问题与解决方案

| # | 问题（第一条真实错误） | 根因 | 解决方案 |
|---|---|---|---|
| 1 | `make: cc: No such file or directory` → `make: *** [Makefile:63: gregor.o] Error 127` | 上游 Makefile 用 `$(CC)`，make 默认 `CC=cc`，本平台 PATH 无 `cc` | 配方从 `self.conf.get("tools.build:compiler_executables")` 取 clang 并显式传 `CC=`（R33：不依赖裸 shell 变量） |
| 2 | `gregor.c:79:12: error: cannot assign to variable 'isleap' with const-qualified type 'const int'` | 上游 `const int isleap;` 声明后又赋值，违反 const 语义，现代编译器一律拒绝 | `build()` 内源码改写 #1：`const int` → `int`（语义不变） |
| 3 | `readtab.c:32:10: fatal error: 'obstack.h' file not found` | musl/HarmonyOS 不提供 GNU obstack（本机无该头文件）；制品仓按 **4 个精确名** `obstack`/`gnulib`/`libiberty`/`gnu-obstack` 检索均 NOT FOUND —— ⚠ **此检索漏了 `musl-obstack`**：`musl-obstack/1.2.3` 实测**在库**（`archives/m/musl-obstack/1.2.3/`、`_index.yaml` 在册 uploaded、`status: built`），且被 `dwarves/1.30:56`、`dwz/0.16:39`、`box64/0.4.4:56`、`elfutils/0.195.1:119` 等 4 个配方直接 `requires` | **仍选 vendor**（口径见下）：**GNU C Library** 的 `obstack.h`+`obstack.c`（经 gcc-mirror 的 `include/` 与 `libiberty/` 取得；LGPL-2.1-or-later，**LGPL-2.1 §6 允许重标注为 GPL v2+**，与上游 GPL-2.0-or-later 静态链接兼容）到 `third_party/obstack/`，`exports_sources` 随配方走、`source()` 摊平进源码树；`CPPFLAGS=-I.` 因 readtab.c 用 `<obstack.h>` 尖括号引入 |
| 4 | `make: install: No such file or directory` → `Makefile:67 installdirs Error 127` | 本平台无 `install(1)`（coreutils 把它装成 `ginstall`） | make 变量覆盖 `INSTALL_DIR="mkdir -p"`、`INSTALL_PROGRAM=cp`、`INSTALL_DATA=cp` |
| 5 | `anacron: Can't open temporary file: Read-only file system` | `runjob.c` 用 `tempnam(NULL, NULL)` → `P_tmpdir` = `/tmp`（只读，E002）。**实测本平台 libc 忽略 `$TMPDIR`**：显式设 `TMPDIR=<可写>` 后 `tempnam(NULL,NULL)` 仍返回 `/tmp/temp_*` | `build()` 内源码改写 #5：`tempnam(".", "an")` —— `main()` 已 `chdir()` 进由本包自有的 spool 目录 |
| 6 | `anacron: getpwuid() error: No such file or directory` → `Aborted` | `/etc/passwd` 存在（15382 B）但**本进程 uid 20020084 不在其中**（HarmonyOS 应用/沙箱 uid 不入系统用户库）⇒ `getpwuid()` 返回 NULL ⇒ 上游 `die_e()` 直接中止；而该地址只用于写邮件 `From:`/`To:` 头 | `build()` 内源码改写 #6：`getpwuid` 失败时退回 `$LOGNAME` → `$USER` → `"anacron"`，不再中止整轮运行 |
| 7 | 首版 test_package 把 scratch 写进 `test_package/` 源目录 | 无 `layout()` 时 `self.build_folder` 就是被 git 跟踪的配方目录；`/tmp` 只读、`$TMPDIR` 又指向家根 | scratch 改落 `~/tmp/anacron-tp-*`（家目录分区的可丢弃产物区），并把该目录作为 `PWD` 传入（E386 的 bash getcwd 种子） |
| 8 | **`finish` Step3 G0 三轮全红**：`finish.log:34` / `finish2.log:37` / `finish3.log:37` 均为 `❌ G0: configure 失败 (exit 127)`，`finish3.log:52` 另有 `⚠️ G0 干净构建验证失败` | 本包是**裸 Makefile、根本没有 configure 脚本**，而 G0 的 clean-verify 仍按带 configure 的入口去跑 `./configure` ⇒ 127（文件不存在）。**与 `经验库/12b-…12.40.md:105` 同一机制**（该条原文讲 CMake 项目「没有该入口时会得到 exit 127」，本包是 makefile 项目同理） | 归类为**框架检查入口不适用**，**非阻塞**（Step3 失败处理=非阻塞，实测后续 G1/G2/G3 全过 + W3 `Pass rate: 100.0%` + 消费者 7/7 全绿）；按该条要求「**W4/PR 中必须明确说明该边界**」，故在本表、`reports/test-report.md` 与 PR `## 补充说明` 三处披露；**⛔ 不为迎合 G0 去给本包造一个假 configure**（后续 finish4-6 三轮同样 exit 127，最新 `finish6.log:38`，读数未变） |
| 9 | `finish` Step7 `⚠️ 存在知识遗漏: pending=0 failed=0 unreferenced=7` + `manifest.yaml: knowledge_count=7 unreferenced=7`、`.knowledge-done` 标记缺失 | **全仓系统性口径，非本包缺陷**（W4 第 2 轮实读 `check_knowledge_gap.py:54-84` 判定）：本包 7 条 `knowledge_gained` 未写 `ref:`；抽样 **40 份含 `knowledge_gained:` 的 manifest，35 份同样 `unreferenced>0`**、全仓 **8161 份含该块仅 14 份含 `knowledge_ref`**；且 **`submission.py` 不读 `.knowledge-done`**，故它**不是 submit 门禁** | **只披露、不修**：⛔ 不给 7 条补 `ref:`、⛔ 不动 `manifest.yaml`（改它会进 HEAD ⇒ 触发审计输入重出，而它既非门禁也不阻塞）。同轮 `EXIT_CODE=0`、`Step10 ✅✅ submit 就绪`，`unreferenced` 读数**保持 7** |
| 10 | **审查整改项：源 URL 协议 http→https**（`conandata.yml` `sources.url`） | 审查 `review-memory.md` 第 12 条「conandata.yml 规范：URL 必须 HTTPS」；第 13 条另要求官方正式源/权威镜像 | `http://deb.debian.org/...` → **`https://deb.debian.org/...`**，**同一上游文件、sha256 不变**。读数：sha256 三方（`conandata.yml` / 登记表备注 / 本地预下载件实测）一致 = **`ceee7520bc49f861499f7eff4c7990d21d39d8a1d3e24449947a7ed5aa34761d`（len=64）**；https 下载实测 **HTTP OK / 24085 B**，与本地预下载件 **`cmp IDENTICAL`**；PR 正文原误写串首差 @4 位（本地 `7` / 正文 `e`）已 PATCH 为权威值并 GET 回读确认。PF7 判据仍命中（Debian 重打包源）—— 协议改动不消除该判据 |
| 11 | **审查整改项：`test_package/test.sh` 补 `set -uo pipefail`** | 原头部仅 `set -u`，`ver="$(anacron -V 2>&1 \| head -1)" \|\| fail` 这类**管道守卫只看管道末命令**的退出码 ⇒ 首段（`anacron -V`）非零时会被判绿、`\|\| fail` 失效 | `set -u` → **`set -uo pipefail`**。实测三读数：① **A/B 对照 A 臂（带 pipefail）rc=0、7/7 PASS、`ALL TESTS PASSED`**，B 臂（临时去掉）同样 7/7 ⇒ 无害；② 最小验证 `set -u; v="$(false \| head -1)"` **不触发** `\|\| fail`，`set -uo pipefail` 下 **触发** ⇒ 守卫生效；③ 正常路径 `anacron -V \| head -1` **不误伤**（无 SIGPIPE 误报）。根因链备查：首轮真跑曾红（`getpwuid() error`），系 `find … \| head -1` 取到**旧 cache 残留二进制** `anacrdf937317c1d74`（mtime 05:19、无 `getpwuid` 兜底），按 mtime 取最新 `anacrc8c35964324f4`（mtime 07:36、含兜底）后即 7/7 —— **非 pipefail 所致** |

## 源码修改

**交付口径 = 「源码级改写放 `build()` 内、不进 `patches/`」**（依据 `经验 §12.50⑤`）：
`finish` Step1 的 `refresh-patch --auto` 会按探索树的 `edit-tracker` 重新生成 `patches/`，
并把手写补丁挪进 `patches/.patch-backup-<ts>` —— 该**隐藏目录会被 CI junk 门禁拦下**、
`conandata.yml` 的引用同时失效导致 G2 红。同条经验记录了 gnuspool #10775
**两连败后统一为本口径**的过程，故本包全程只用这一种口径（本包曾先用补丁集、
被 Step1 破坏一次，已按该条改口径）。

六处改写固化在 `conanfile.py::_SOURCE_FIXES`，由 `build()` **幂等**应用
（锚点已替换则跳过；锚点丢失则显式报错，绝不静默跳过）：

| # | 文件 | 改动 |
|---|---|---|
| 1 | `gregor.c` | `const int isleap;` → `int isleap;` |
| 2 | `main.c` | 增加 `<stdlib.h>`（`getenv()` 需要） |
| 3 | `main.c` | `chdir(SPOOLDIR)` → 先读 `ANACRON_SPOOL`，缺省仍用 `SPOOLDIR`，消息改 `printf` 形式 |
| 4 | `main.c` | 声明 `char *spool_dir;` |
| 5 | `runjob.c` | `tempnam(NULL, NULL)` → `tempnam(".", "an")` |
| 6 | `runjob.c` | `username()`：`getpwuid` 失败不再 `die_e()`，退回 `$LOGNAME` → `$USER` → `anacron` |

- **`patches/` 目录不存在**，`conandata.yml` 为 `patches: {}`；
- **不引入任何 `__OHOS__` 平台宏**（PF5 判据针对 `patches/*.patch` 新增行，本包无补丁文件 ⇒ 天然不触发；六处改写里也无该宏）。

`third_party/obstack/` 的两个文件是**配方携带的额外源文件**（vendor 输入），
经 `exports_sources` 随行、`source()` 摊平进源码树，由上游 Makefile 的 `wildcard *.c`
纳入 `objects` —— 同样不进补丁集。

## 依赖版本

- 第三方 conan 依赖：**0 个**（`preflight_check.sh anacron/2.3` → `预检通过（无依赖需要检查）`，rc=0）
- vendor：**GNU C Library** 的 `obstack.h`/`obstack.c`（经 gcc-mirror 取得；LGPL-2.1-or-later），随配方 `exports_sources` 分发，不作为独立包
- ⚠ **口径更正（W4 P1-2）**：制品仓**并非没有** obstack 实现 —— `musl-obstack/1.2.3` 在库且被 4 个配方 requires；本轮初版检索词只用了 `obstack`/`gnulib`/`libiberty`/`gnu-obstack` 四个精确名、**漏检 `musl-obstack`**，因此「查无才 vendor」的说法不成立。**本包仍选 vendor**，理由是 application 包免引入 shared 依赖与 SONAME 打包面 + 许可证兼容有据（LGPL-2.1 §6），**不是**因为查不到

## 测试口径（★ 与 `manifest.yaml`、交付说明三处同源；**实测自数**）

### 上游测试 = **0**（`§12.72` 资产口径，四类逐项）

对 24085 B / sha256 `ceeee75…61d` 的 orig tarball 全树（**18 条目 = 1 目录 + 17 文件**，`tar tzf … | wc -l` 实测）清点：

| 类别 | 口径 | 实测 |
|---|---|---|
| ① 独立测试框架 | `test*/` 目录、`test*.c`/`test*.sh`/`*_test.c`/`check*.c` | **0** |
| ② 测试语料 | `*/res` 目录 | **0** |
| ③ 测试脚本 | `**/*RUNTEST*` | **0** |
| ④ 示例程序 | `src/demo`、`src/examples`、顶层 `demo`/`examples` | **0** |
| **合计** | | **0** |

判定依据：上游 `Makefile` 的 `.PHONY` 只有 `all/installdirs/install/clean/dist/release`，**没有 `check` 目标**；`MANIFEST.yml` 的 `upstream_check_command` 因此留空。这不是"未注册进构建系统"，而是**源码树里根本没有测试资产**。

### 消费者测试（test_package）= **7**

`test_package/test.sh` 7 个正向断言（另含 8 条负向失败守卫）：

1. `anacron` 可从 `conanrun` PATH 解析
2. `anacron -V` 版本串 == `Anacron 2.3`
3. anacrontab 被解析且 job 被调度
4. job 经 `fork/exec` + `/bin/sh -c` 真实执行（marker 文件落地）
5. spool 时间戳文件 `<spool>/<job-id>` 生成
6. `ANACRON_SPOOL` 覆盖口确实作用于 `chdir()`（指向不存在目录时报 `Can't chdir` 并非零退出）
7. `-u` 只更新时间戳、不执行 job

### 合计断言 = **7**

**上/下游不同时的说明（`## 补充说明`「测试数量变化原因」所需口径）**：上游实测 0、适配后 7 —— 适配后 ≥ 上游，无需豁免章节；上游 0 是**资产缺失**（不是跳过），已在 `test_package/MANIFEST.yml` 与本节给出四类清点证据。

## 验证结果

```bash
$ conan create archives/a/anacron/2.3 -pr:h=.../ohos-aarch64 -pr:b=.../ohos-aarch64
rc=0

PASS: anacron resolves to <cache>/p/b/anacr…/p/bin/anacron
PASS: version banner: Anacron 2.3
Anacron 2.3 started on 2026-10-06
Will run job `smokejob'
Jobs will be executed sequentially
Job `smokejob' started
Job `smokejob' terminated
Normal exit (1 jobs run)
PASS: anacrontab parsed and job scheduled
PASS: job executed via fork/exec + /bin/sh -c
PASS: spool timestamp created (…/spool/smokejob)
PASS: ANACRON_SPOOL override reaches chdir()
PASS: -u updates the timestamp without running the job
ALL TESTS PASSED
```

**能力面复核**（本机实测，与派卡读数一致）：

| 能力 | 实测 |
|---|---|
| `fork`+`exec` `/bin/echo` | rc=0，`ok` ✅ |
| `SIGUSR1` 自发自收 | 收到 1 次 ✅ |
| `alarm()` | OK ✅ |
| `/var/spool/anacron` | 不存在（**`/var/spool` 父目录本身也不存在**）❌ |
| `/etc/anacrontab` | 不存在 ❌ |
| `/var/lib/anacron` | 不存在 ❌ |
| `/etc/localtime` | 不存在 ⚠ |
| `/tmp` 可写 | **False**（`OSError [Errno 30] Read-only file system`）= 已知 E002 ⚠ |

定性：**不是能力墙** —— 核心三能力全可用，spool/anacrontab 是**安装时由本包自己创建**的（`make install` 的 `installdirs` 会建 `<package_folder>/var/spool/anacron`），不依赖内核特性或系统预置服务；`/tmp` 只读已用「临时文件改落自有 spool 目录」绕开。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/anacron` | 定时补跑守护（ELF arm64） |
| `share/man/man5/anacrontab.5` | anacrontab 手册 |
| `share/man/man8/anacron.8` | anacron 手册 |
| `var/spool/anacron/` | spool 时间戳目录（随包创建） |
| `etc/anacrontab` | 默认配置文件位置（随包创建，运行时可用 `-t` 覆盖） |

## 注意事项

- **spool 目录的运行时覆盖口是 `ANACRON_SPOOL` 环境变量**（本次新增，见源码改写 #3）。上游 `-t` 只能覆盖 anacrontab、覆盖不了 spool；不设该变量时使用编译期烧死的 `<package_folder>/var/spool/anacron`。
- **跨机复用二进制时必须设 `ANACRON_SPOOL`**：编译期宏绑定本机 conan cache 路径，二进制从远端下载到别的 cache 时默认 spool 路径不再存在（本机/CI 各自 `conan create` 则不受影响）。
- 邮件功能（`MAILTO`）依赖 `/usr/sbin/sendmail`（`global.h` 烧死）——本平台无 MTA，配置了 `MAILTO` 的 job 会投递失败；不配置 `MAILTO` 则完全不受影响（测试即按此路径验证）。
- `/etc/localtime` 不存在 ⇒ 与"按本地时间排程"相关的显示可能为 UTC；不影响本包的时间戳比较逻辑（用的是 `day_num()` 的儒略日计数）。
---

**编译结束**: 2026-10-07 00:01
**最终状态**: built
