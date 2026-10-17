# ries 2018.08.05 适配笔记

## 概览

- 软件：RIES —— 给定一个数值 T，搜索"解等于 T"的代数方程（作者 Robert P. Munafo，上游主页 <https://mrob.com/pub/ries/>）。
- 版本：任务/归档/分支/配方版本串一律 `2018.08.05`（发行版侧日期版本号）。二进制自身打印的却是源码内 `#define RIES_VERSION "2018 Aug 12"`（`ries --version` 实测首行），两者不等属上游口径，未做任何"归一化"。
- 构建系统：GNU Make，入口文件是 **GNUmakefile**（不是 Makefile）；无 configure、无 autotools、无外部依赖，唯一链接参数 `-lm`（OHOS libc 自带）。
- 体量：上游 tarball 共 3 个文件（ries.c 458048B、ries.1 71534B、GNUmakefile 513B），单个 C 翻译单元。
- 语言预检（R47）：`lang-preflight ries 2018.08.05` → rc=0，`detected_language=c`，task=cpp，c↔cpp 兼容族放行（证据：`language_evidence.source_stats = 源文件 1 个（c:1），主体占比 100%`）。
- 产物：`bin/ries`（application）+ `share/man/man1/ries.1`；`package_type="application"` → 按 R38 在软件级目录声明 `commands.json`。

## 构建环境

- 机器：HarmonyOS PC aarch64（B 机，构建主机）；clang 15.0.4（`/data/service/hnp/bin/clang`）、GNU Make 4.4.1；产物 `ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)`。
- `CONAN_HOME=$HOME/tmp/ch/home-ries`（全新 conan 2.29.1 home，含 `extensions/plugins/profile.py`）；remote `ohpcd` 已加、`conancenter` 已禁用；profile `ohos-aarch64`。
- 标准环境变量：`SSL_CERT_FILE=$HOME/usr/local/ssl/cert.pem`、`PATH` 前置 `$HOME/usr/local/bin:$HOME/.local/bin`。

## 适配点（症状 → 根因 → 最小复现 → 已试过的失败方案 → 最终方案 → 适用边界）

### A1 上游 `install` 目标在本平台跑不通（唯一实质改动）

症状与最小复现（B 机，源码目录内）：

```
$ make -f GNUmakefile install DESTDIR=$HOME/tmp/uc2/z45-ries/stage PREFIX=/usr
mkdir -p .../stage/usr/bin .../stage/usr/share/man/man1
install -m 0755 ries   .../stage/usr/bin
make: install: No such file or directory
make: *** [GNUmakefile:18: install] Error 127
INSTALL_RC=2
```

根因：GNUmakefile 第 19–20 行用宿主 `install(1)` 程序落文件；OHOS worker 上只有工具链 + toybox，没有 coreutils 的 `install`（`command -v install` 无结果），同一条 make 规则里的 `mkdir -p` 却可用 —— 失败点精确在 `install` 这个程序名上（Error 127 = 命令未找到）。

已试过的失败方案：

1. `make install DESTDIR=<stage> PREFIX=/usr`（上面的 rc=2）。
2. 先 `make` 再补一条 `make install`：同一条规则，同样 127。
3. 引入 coreutils/`ginstall` 作为 `tool_requires`：**未采用**——本包只有一个可执行文件 + 一个手册页，为省两行 copy 去拉一条 coreutils 依赖链，代价（依赖发布顺序 R36、worker 上 ~/usr/local 注入面 R49/E524）明显高于收益；且 CI 环境并未预装。

最终方案：`build()` 只跑 `make -f GNUmakefile CC=<conan conf 里的 c> -j1`（R33 编译器取自 `tools.build:compiler_executables`，R9 恒 `-j1`），`package()` 用 Conan 的 `copy()` 把 `ries` → `bin/`、`ries.1` → `share/man/man1/` 落位，权限交给 conan 打包，不依赖宿主 `install(1)`。CFLAGS 保持上游 `?=` 默认（`-g -O2 -fstack-protector-strong -D_FORTIFY_SOURCE=2`），OHOS clang 15 下零告警零错误（见 `logs/manual-make.log`），按 R1"参数最少化"不额外注入。

适用边界：任何 Makefile 家族的 `install:` 规则里直接调用 `install(1)`（含 `install -m/-d/-D/-C`）的包。签名稳定：`make: install: No such file or directory` + `*** [<file>:<line>: <target>] Error 127`。

### A2 GNUmakefile 的 `/usr/local` 是默认值，不是烧死路径（台账矛盾判定）

读数原文（`GNUmakefile` 第 10–20 行，逐字）：

```
DESTDIR?=
PREFIX?=/usr/local
BINDIR?=$(PREFIX)/bin
MANDIR?=$(PREFIX)/share/man

.PHONY: install clean
install: ries ries.1
	mkdir -p $(DESTDIR)$(BINDIR) $(DESTDIR)$(MANDIR)/man1

	install -m 0755 ries   $(DESTDIR)$(BINDIR)
	install -m 0644 ries.1 $(DESTDIR)$(MANDIR)/man1
```

判定：四个路径变量全是 `?=`（未定义才赋值），`BINDIR/MANDIR` 又由 `$(PREFIX)` 递归展开，命令行或环境给 `PREFIX=`/`DESTDIR=` 即穿透到 install 行（A1 的复现日志里 `mkdir -p .../stage/usr/bin` 就是 `PREFIX=/usr DESTDIR=<stage>` 生效的直接证据）。⇒ **"烧死系统路径" = False**，M18 信号按本读数落定（台账同一行的两句互斥表述以此为准）。
配方侧因此无需任何绕路：不出现 `/usr/local` 字面量，落位由 `self.package_folder` 决定，PF6/R49 前缀闸天然干净。

### A3 取源：上游无版本归档，PF7 与"版本串必须完全一致"打架（需主理裁决）

- 上游只发布**滚动单文件** `https://mrob.com/pub/ries/src/ries.c.txt`；`src/` 目录列表实测只有 9 个滚动 `.txt`，无任何 `.tar.*`/`.zip`；版本化命名候选全部 404（`src/ries-2018-08-05.tar.gz`、`/pub/ries/ries-2018.08.05.tar.gz`、`src/ries.c.txt.2018`、`/pub/ries/old/`）。
- 现网滚动文件已漂移：头部 `This is the 2026 May 06 version of "ries.c"`，462229B，sha256 `df335f024d5ebd18134386edb7ca29ab25981c8b2e44be55b7a811d80bb57621`；2018.08.05 的 `ries.c` 是 458048B、sha256 `73f77c1a91496056e5bf7629a848f002055554077793d323edf2c9f2c560152b`。**⇒ 用官方滚动 URL 就是拿 2026-05-06 的代码冒充 2018.08.05**，违反"版本串完全一致、不得归一化"，不可取。
- 带时间戳的官方快照（Wayback）取不到：Windows 侧与 B 机对 `web.archive.org`（http 与 https 各一次）均 `curl: (28) Connection timed out`，CI 同网段更不可依赖。
- 当前唯一可稳定取到钉版字节的公开源 = Debian pool `ries_2018.08.05.orig.tar.xz`：139344B，sha256 `725c004f5a252c3284b77189043c05ca9b57551bcc0e1c57b65d0ddcf45786b9`，与该机 `.dsc` 的 `Checksums-Sha256` 逐字节一致；`.dsc`（Format: 3.0 quilt）内的 `debian/patches/` 只有两个补丁，均只动 `ries.1`（拼写、man section），**`ries.c` 未被下游修改**（B 机实测下载 + 解包 + `sha256sum` 取证）。
- 冲突点：`scripts/ohc/preflight.py` 的 PF7 源URL闸把 `deb.debian.org` 写进 `_PF7_DEBIAN_HOSTS`，凡本 PR 变更的 `conandata.yml` 出现即**硬拦建 PR**（判语 "Debian 下游重打包源"）；仓内另有 307 份 `conandata.yml` 已在用该域，均为 PF7（SKILL v12.20，2026-09-03）上线前的存量。
- 处理：本包**保留 Debian orig URL**（这是"版本必须完全一致"的唯一可复现解），并按 PF7 自己给出的口径申报例外——"确属官方托管例外须 PR 说明并 `--no-preflight` 跳过"。请主理在建 PR 时二选一：①保留本 URL，正文写明"上游无归档 + Debian orig 内 ries.c 为上游原样 + sha256 与 .dsc 对齐"三点证据并 `--no-preflight`；②改按上游滚动 URL 适配、把版本改成上游自身日期版（需平台任务版本变更，本包无权擅改）。
- 附带事实（若要彻底去下游化时备用）：orig tarball 里的 `GNUmakefile` 头部是 `# Copyright © Nicolas Braud-Santoni`（Debian 维护者所写，非上游作者产物）；上游自己的构建说明写在 `ries.c` 头部 HOW TO BUILD：`gcc -o ries ries.c -lm`。当前配方沿用该 GNUmakefile 只为复用同一份 CFLAGS/`-lm` 链接参数；如评审质疑"依赖下游打包件"，可一行改成 `self.run(f"{cc} ries.c -lm -o ries")` 并删掉 `-f GNUmakefile`，构建结果等价（同一条命令已手工验证可过）。

## R51 上游测试清点（一手依据）

```
$ make -f GNUmakefile -n check   ->  make: *** No rule to make target 'check'.  Stop.   (rc=2)
$ make -f GNUmakefile -n test    ->  make: *** No rule to make target 'test'.   Stop.   (rc=2)
GNUmakefile 目标全集：ries:（默认，第 7 行） / install:（16） / clean:（22）；.PHONY: install clean（15）
find . -iname '*test*' -o -iname tests  ->  空
grep -c "ck_assert\|unit_test\|assert(" ries.c  ->  0
```

⇒ 上游测试**静态总数 = 0**：不是"有测试但本机跑不动"，而是根本没有测试目标、测试源文件与断言框架。未使用任何 `--disable-*` / `DISABLE_TESTS` / `no-check` 之类凑绿手段。

## 测试五维账本

| 维度 | 数字 | 依据 |
|---|---|---|
| 上游测试静态总数 | 0 | 上节 `make -n check/test` rc=2 + 目标全集读数 |
| 上游可执行测试数 | 0 | 同上（无目标可执行） |
| 上游实测通过数 | 0 | 无可执行项 |
| 适配后新增消费者用例 | 9 | `test_package/test.sh`（真实调用安装后的 `ries`） |
| 新增用例实测 通过/跳过/失败 | 9 / 0 / 0 | 原件随 PR：`reports/w3-local-ci.log` 第 224 行 `RIES_TEST_SUMMARY total=9 passed=9 failed=0`（本轮 `conan create` 的 test_package 实测），同臂复跑 6 轮见 `reports/assert9-fixcheck/new1-6.log`；断言 9 口径见下节修订记录，判决以 `VERIFY_RC` 与门禁标记同源（设备侧 `~/tmp/uc2/z45-ries/logs/` 的中间日志属可丢弃区，不随 PR） |

PR 正文按本表回填，声明用例数 = 实测数，不做"上游通过率"表述（分子分母皆 0）。

## 平台/框架现象（如实披露，不算本包失败）

1. **`init-build` 假红**：`scripts/ohc/check_env.py:33` 写成 `except Exception: return False, str(e)`，`e` 未绑定 ⇒ 任何"能被 `shutil.which` 找到但无法 `execve`"的工具都会把 init-build 打成 `NameError: name 'e' is not defined`（本机 `~/usr/local/bin/automake` 是缺 perl 解释器的脚本，实测触发）。本包 GNUmakefile 不需要 automake，属纯假红；按 R12"脚本失败=手动模式入口"继续：手工 `make` rc=0、`--version`/求解冒烟 rc=0，再走 `conan-init`→`conan-verify`→`finish`。修 `as e` 属框架改动，需单独 PR（本 PR 不含）。
2. **`init-build` 构建系统误判**：把本包按 `autotools` 建档（`manifest.yaml` 里 `build.system: autotools`、`tar_format: tar.gz` 均为模板默认值），已按实测改回 `makefile`/`tar.xz`；这也是上一条探针被吃到的直接原因。
3. **L2 若报 `L2_RESULT=skip` 属框架预期**（CI 裸跑 bin 不载 runenv），既不是失败也不能当可执行证据；可执行证据是 test_package 的 9 条真机用例。
4. `recipe-search ries` 无相似命中（语料 6173 条，判语"首稿走 conan-init 模板"）；`recipe-search ries -b make` 命中 critnib/1.1 等，实际底稿取 `archives/2/2048.c/1.0.3`（同为单文件 C + make + application + 配方内 copy 落位，形态最接近）。

## 断言 9 修订记录（第 2 棒子代理，2026-09-25）

首稿断言 9 写作「两次 `ries -n3 2.5063` 的输出 `cmp` 逐字节一致」，实测**不可复现**：
18:42 那轮 9/9 通过，18:50 同树同机同 conan 重跑即变 `total=9 passed=8 failed=1`。
被引的那份 18:50 轮 W3 日志**已被 19:05:37 末轮原地覆写**（`reports/w3-local-ci.log` 由框架按
同一路径重写，随 PR 的是末轮原件，第 224 行 `RIES_TEST_SUMMARY total=9 passed=9 failed=0`），
故翻面那一轮以**同臂复跑件**随 PR 保存：`reports/assert9-fixcheck/old4.log` =
`RIES_TEST_SUMMARY total=9 passed=8 failed=1`（sha256 `a1482ac7a4185f3d...`），同一脚本
同臂另外 5 轮 `old1/old2/old3/old5/old6.log` 均 9/9（sha256 同为 `d103f1193fb54661...`）
⇒ 翻面是随机事件，不是某一轮的树或环境差异。

根因（一手证据随 PR：`reports/assert9-det3/` 与 `reports/assert9-fixcheck/`，
逐件 sha256 与搬运对账见 `reports/knowledge-candidate-ledger.md` 附表）：
本包 `-n3` 的搜索结果本身是确定的，但 ries 在收尾摘要里打印一枚**墙钟秒表**——
`ries.c:7540` `printf("  Time: %.3f\n", tsec)`，`tsec = gettime()`（`:7511`）。
它只受 `g_enable_output` 约束（`--find-expression` 一类非交互用法会整块抑制统计，
不是消费者冒烟用例的形态），正常 CLI 输出里无法单独关掉。B 机 aarch64 实测 30 次
`ries -n3 2.5063`：整份输出 **2 种 md5**（该字段读作 `0.000` / `0.001`），
掩掉该字段后 30 次 **1 种 md5**；再放一枚竞争进程，连续两次的原始 `cmp` 即 rc=1，
`diff` 只落在第 13 行 `dead-ends: … Time: 0.000` ↔ `0.001`。⇒ 机器越忙、越容易翻面，
这正是 18:42 绿、18:50 红的差别（当时 B 机另有窗在构建）。

排除项（逐条一手读数）：
1. ries 伪随机 / 未初始化残留 —— 源码里的 `rand()` / `srand` / `random()` / `getpid` /
   `arc4random` **作为可执行调用 0 命中**（探针件 458048B 实测：`srand`、`getpid`、`arc4random`
   字面各 0 命中；`random` 字面 3 处 = `:105`、`:2479`、`:2575`，全在注释散文里；`rand(` 字面 1 处
   = `:106` 的注释公式 `e^(K*erf(rand(0..1)))`。按调用式再查
   `(^|[^A-Za-z_])rand *\(|random *\(|srand *\(|drand48 *\(|getpid *\(|arc4random *\(`
   全文只命中 1 行，就是 `:106` 那条注释 ⇒ 可执行调用为 0）；
   `Memory: 12608 B`、`Total equations tested: 7315`、
   `dead-ends` 等计数 30 跑恒定 —— 随 PR 的 `reports/assert9-det3/md_mask.txt` 显示掩掉 `Time:`
   字段后 30 跑只剩 **1 种** md5，即除该字段外每一个字节都恒定。
2. 参考输出落点被第二轮覆写：两臂都写同一 `$WORK`（`$TMPDIR/ries-test.$$`），
   `test_package/` 下无 `out9a.txt` 残留（`git status --untracked-files=all` 干净）
   ⇒ 未触发 `mkdir` 失败的 `WORK=.` 回退，也不存在与 L1e 负照轮共用落点的问题。
3. CWD / env 三臂：修订前后都在 conan 的 `conanrun.sh` 同臂、`cwd=test_package` 下做 6 轮对照，
   旧断言第 4 轮复现 `passed=8 failed=1`（rc=1），新断言 6 轮全 9 通过（rc=0）。
4. 两跑之间树变化：期间只多一枚 notes 时间戳提交，`notes.md` 不在 `export_sources`
   （配方未定义 `exports`）⇒ 不改 recipe revision；当时 `conandata.yml` 干净。

修订后的断言 9 = 「掩掉秒表字段后逐字节一致」**加**字段级正对照（把**同一条**字段级 sed
应用到两臂后再 `diff`，除 hunk 头外输出必须为空）：等式列表、`max complexity`、`dead-ends`、
`expressions`、`distinct`、`Memory`、`Total equations tested` 全部仍在逐字节比较面内。
**未删除该断言、未缩分母（仍 9 条）、未加吞 rc 兜底与 SKIP 通道**。
第 2 棒的正对照曾写成行级 `grep -vE '...|Time: '`（含 `Time:` 的整行不算未处置差异），而 ries
把秒表与 `dead-ends` 三个计数印在**同一行**（第 13 行
`dead-ends: 2581 1907 4488  Time: 0.001`）⇒ 行级排除会把同行上的非时钟差异一并放过，
声称强度高于实际，故第 3 棒改为字段级。合成反例对照读数：同一对文本在第 13 行同时改动
`dead-ends` 计数与 Time 值时，行级排除的未处置差异 **0 字节（盲）**、字段级 **159 字节（抓到）**
且 `norm_rc=1`；改后 `test_package/test.sh`（sha256 `8c6f5d0df0563537...`）在 6 枚 spinner
负载下同臂复跑 4 轮全部 `total=9 passed=9 failed=0`、rc=0 —— 两笔读数同见随 PR 的
`reports/assert9-fixcheck/harness-recheck.log`（A/B/C 三节，取数脚本 `harness-recheck.sh`）。
定性：**消费者 harness 自身把不可复现的秒表字段纳入了逐字节比较**，属测试件缺陷，
不是 OHOS / 工具链 / 依赖 / 上游缺陷。

## 路径 B 判定

**B判定=create(DRAFT-ries-2018.08.05-self-reported-timing-field-in-byte-comparison)**
—— 本 PR 的知识位给「消费者断言不得把被测程序自报的计时字段纳入逐字节比较」这条新机制
（四范围查重读数与层次差对齐见同目录 `reports/knowledge-candidate-ledger.md` 候选 3 节）。

- **适配路径**：路径 A + 路径 B —— A 为配方侧 manual-install 落位（不改上游源码、无补丁）；B 新增一条机制知识：确定性求解器正常输出里那枚不可抑制的墙钟字段被纳入了消费者逐字节断言 ⇒ 随机假失败，修法为字段级掩码 + 字段级正对照。
- **使用知识库**：E174（`knowledge/graph/E174.kv:5,13,17,22-23`、`knowledge/doc/E174.md:11`、`knowledge/operations/filesystem-analysis.md:271`）按文件名作 hit 引用；`recipe-search ries` 语料 6173 条零命中（判语"首稿走 conan-init 模板"）。
- **知识库扩展**：`knowledge/drafts/DRAFT-ries-2018.08.05-self-reported-timing-field-in-byte-comparison.kv` 与同名 `.md`（成对新草稿，即上述计时字段机制）。
- **关联 Issue**：#3416（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3416）

E174 那一面（A1 的 `make install` 缺 `install(1)`）经 W4 独立审计复算为**行号级引用逐条命中**，
按文件名保留为 hit 引用、**不占本 PR 知识位**；四条件逐条核与全部行号级引用见同目录
`reports/knowledge-candidate-ledger.md` 候选 1 节；A3（取源/PF7）为何不升 B 见该台账候选 2 节。
---

**编译结束**: 2026-09-25 19:05
**最终状态**: built
