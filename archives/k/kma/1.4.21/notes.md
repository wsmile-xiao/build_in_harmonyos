# kma 1.4.21 适配笔记

## 编译环境
- 构建系统: makefile（上游只有 Makefile，无 configure/cmake/meson）
- 编译日期: 2026-09-25
- 编译器: clang / clang++（conan conf `tools.build:compiler_executables:c`），归档工具 llvm-ar
- 状态: built
- 目标平台: HarmonyOS PC（ohos-aarch64 profile，musl libc）

## 编译步骤

上游无 configure/cmake，全部走 make 命令行变量覆盖：

1. `conan build` 内取 zlib 的 `package_folder`，拼 `-I<zlib>/include`、`-L<zlib>/lib`。
2. 命令行赋值 `CC`、`AR`、`CFLAGS`、`LDFLAGS` 后执行 `make -j1 all`。
   GNU make 语义：命令行赋值的变量优先级最高，会屏蔽 Makefile 里的
   `CFLAGS += -std=c99`，因此必须把 `-Wall -O3 -std=c99` 三项在命令行显式重述，
   否则 C99 语法回落到默认 std 并报不兼容。
3. `package()` 把 Makefile 产出的四个可执行文件装进 `bin/`：
   `kma`、`kma_index`、`kma_shm`、`kma_update`（纯可执行包，无 lib/、无头文件）。

源码获取（不是编译步骤但记在这里）：上游是 git 仓库
`https://bitbucket.org/genomicepidemiology/kma`。**上游至今不发布任何带校验和的正式
release 工件**——这句话在换源之后仍然成立；本包取的不是官方 release，也没有把它
写成官方 release。上游可下载的只有 Bitbucket 按 ref 即时生成的快照，本轮
（2026-09-25）在 B 机复测 tag `1.4.21` 那一份：HTTP 200、`application/x-tar-gz`、
690007 字节、sha256
`fb6dc991d8777df49f0d02fadf6ccb7800531a68a5c22800de9f324d29f5750e`；对照组不存在的
ref `/get/v1.4.21.tar.gz` 回 HTTP 404 + 23 字节 `text/plain`，且该响应体被 `tar tzf`
直接判为 not gzip ⇒ 端点确按 ref 区分、快照确实可得。该快照由**移动 tag** 即时生成，
自身不带任何上游公布的校验和，故 `conandata.yml` 与两级 manifest 里 pin 的 sha256
是**本机实测值**，不是上游声明。

**本包取上游官方 tag 归档**（`get/1.4.21.tar.gz`，即上段读数对应的那一份）。它与本包
先前所取的 Debian pristine `kma_1.4.21.orig.tar.xz` 内容逐文件等价，本轮在 B 机复算：
`diff -rq` 两棵解包树 **rc=0、零差异行**，两侧各 **148 个常规文件 / 154 个 tar 条目**，
两侧**逐文件 sha256 清单完全一致**，剥掉顶层目录后的 tar 条目名集合也一致。被替换件
的留档读数：630940 字节、sha256
`fb50e3fa72133285db0f9058060991fa1306f9be492f00f646e62cb7eb49a635`、
`tar tJf | grep -c debian` 实测 **0 命中**（无 debian/ 目录、无 dfsg 式删减）。顶层
目录名两侧不同（`genomicepidemiology-kma-c0dca4d8c4ac` 对 `kma-1.4.21`），配方
`source()` 走 `strip_root=True` ⇒ 不影响构建；`patches: {}` 未变、无补丁应用。为排除
比较器本身哑火，同一轮做了**正对照**：对植入差异的两个目录跑同样两种比对，
`diff -rq` 与逐文件 sha256 清单均报警（`eq4b.out` E 段）⇒ 上面的零差异不是哑火假绿。

**换源的理由是门禁，不是内容**：preflight PF7/R39（`scripts/ohc/preflight.py` 的
`check_source_urls`）对 `deb.debian.org` 这一族域名无条件判作「Debian 下游重打包源」，
而建 PR 前的 `run_preflight` 是 fail-closed（`scripts/gitcode_pr.py:291-297` 调用它，
命令行又不暴露 `--no-preflight`）⇒ 即便两份归档逐文件等价，取 pool 归档也过不了这道
闸。改取上游 tag 归档后，取源链路上不再有下游发行版主机，同时消掉「经 Debian 转一道手」
的间接层。`archives/k/kma/1.4.21/test_package/MANIFEST.yml` 的上游测试清点是对被替换的
那份 pristine 归档做的，因两棵树逐文件 sha256 一致，其读数在新源下同样成立（该文件已
就地注明此事，清点未重跑）。

复算证据件（本轮新建，均不覆盖早先产物）：`~/tmp/uc2/z33-kma-fix/eq4-readings.out`
（下载、条目数、404 对照全量读数）、`eq4b.out`（解包 + 两种比较器 + 正对照）、
`eq4-tag-1.4.21.tar.gz`（690007 字节，sha256 同上）、`eq4-tag-v1421-control.tar.gz`
（404 响应体 23 字节）、`eq4b-diff-rq.txt`（0 字节 = 零差异）、
`eq4b-manifest-tag.txt` / `eq4b-manifest-orig.txt`（逐文件 sha256 清单）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 默认比对路径整体不可用：`kma -i query.fa -t_db db -o out` 退出码 159（128+31=SIGSYS），`out_default.*` 四个输出文件全 0 字节；`kma db -t_db` 同报 159 | 本平台 seccomp-BPF 按 **syscall 号** 把 SysV IPC 击杀成 SIGSYS（`si_code=1 SYS_SECCOMP`，拿不到 errno）：`shmget/shmat/shmdt/msgget/semget/msgsnd/msgrcv` 全部被击杀；`shmctl/msgctl/semctl` 进内核返 EINVAL；`malloc`、文件 `mmap`+`msync`、`shm_open`+`mmap`、`ftok` 放行（逐号读数见 `~/tmp/uc2/z33-kma/probe.c`（探针源码 4151 字节）、`~/tmp/uc2/z33-kma/probe.out`（判决原文 1184 字节）、`~/tmp/uc2/z33-kma/probe-summary.txt`（汇总 542 字节）；编译出的可执行件是同目录的 `~/tmp/uc2/z33-kma/probe`（27008 字节）——该目录下**没有** `probe/` 子目录） | **不改上游一行代码**：上游自带 `-mmap` 文件映射后端（`kma.c:144` 帮助行；`kma.c:525-527` 置 `shm\|=32` 并把 destroy 换成 `hashMapKMA_munmap`；`kmers.c:86-87`、`sparse.c:381-382` 转向 `kmmap.c:33` 的 `hashMapKMAmmap`，纯文件 mmap 后端，本平台放行）。消费者测试即用 `-mmap`，实测 rc=0 且结果与上游语义一致 |
| 2 | 想靠上游兜底绕过：`hashMapKMA_load()` 里 `shmid < 0` 的 **if 分支**走普通文件读（`hashmapkma.c:321` 是 `if(shmid < 0) {`，`fread` 在 :324-330；`:331-335` 的 else 才是 `shmat` 挂载） | 该回退在本平台**不可达**：`hashmapkma.c:319/349/385/416` 的 `ftok`+`shmget` 是无条件执行，`shmid<0` 的兜底在它被判定之前进程已经收到 SIGSYS | 不作兜底使用；改走上游 `-mmap` 显式路径（同 #1） |
| 3 | 首轮构建 C99 语法报错 | `make` 命令行赋 `CFLAGS` 会屏蔽 Makefile 内的 `CFLAGS += -std=c99` | 命令行重述 `-Wall -O3 -std=c99` 后再追加 zlib 的 `-I/-L` |
| 4 | 消费者测试产物污染检出树 | 工作目录若取 `os.getcwd()`（conan 会落在 `test_package/` 下），而 root `.gitignore` 未覆盖本测试的输出名；设备 `/tmp` 只读 | `test_package/conanfile.py` 改为在 `$TMPDIR`（缺省退到 `~/tmp`）下 `tempfile.mkdtemp(prefix="kma-consumer-")` 开唯一子目录，与 CI 自身 `l1e_backup` 口径一致；当前绑定 W3 日志实测路径 `/storage/Users/currentUser/tmp/kma-consumer-31fwb74y`（`reports/w3-local-ci.log:296`、`:299` 两处逐字符一致；mkdtemp 后缀每轮不同，换源重跑前那轮是 `h3vsbau5`，已随该轮失效） |

## 源码修改

无。`patches_applied: []`，`patches/` 目录为空，W3 静态检查 `L4_RESULT=pass: patches clean`。
`-mmap` 是使用方式而不是补丁。

## 依赖版本

- zlib/1.3.1.1（ohpcd 已发布，W0 证据：`~/tmp/uc2/z33-kma/w0-zlib-publication.log`、
  `w0b-zlib-remote-probe.log`）
- 其余为工具链：clang/clang++、llvm-ar、python3（跑 test_package）

## 验证结果

以下三值取自本轮（2026-09-25 06:56–06:57，日志前缀 `g4-`）按当前 HEAD 复跑的读数，落在
`~/tmp/uc2/z33-kma-fix/`；同目录更早的 `r2-` 前缀（05:52–05:54）是**换源重跑之前**那一轮，
它写下的 `reports/w3-local-ci.log` 已被本轮覆盖，故本轮不再引用 `r2-*` 的任何行号。
W3 判决的绑定文件是 `archives/k/kma/1.4.21/reports/w3-local-ci.log`（当前 384 行，sha256
`cb4549bc493390c4cf6ec74e1d298d516262a183c085abb70d86b241a8319078`，与
`archives/k/kma/1.4.21/.ci-result.json` 里 `log_sha256` 字段逐字符相等；该件另记
`exit_code: 0`、`timestamp` = `2026-09-25T06:57:40.459245`）。复算命令两条：
`sha256sum archives/k/kma/1.4.21/reports/w3-local-ci.log` 与
`grep -o 'cb4549bc[0-9a-f]*' archives/k/kma/1.4.21/.ci-result.json`。
另：配方件 `conanfile.py` 与 `conandata.yml` 在仓内的最后一次内容改动是承载本次换源的提交
`936ceeb2dd`（07:00:09 落盘，工作树内容即本轮 06:56–06:57 门禁所跑的那一份），当前 HEAD
`467a8cca73c6` 与本轮整改都不触碰构建输入 ⇒ 下列证据仍绑定当前配方，导出 revision 为
`kma/1.4.21@ohpcd/stable#8e0b36e9f5ad8a6431703b5f31993dd9`（`reports/conan-create.log:9`）：

```bash
# ① conan-verify → ~/tmp/uc2/z33-kma-fix/g4-2-verify.log:22（✅ 配方验证通过: kma 1.4.21）；
#    整体 rc 见 ~/tmp/uc2/z33-kma-fix/g4-main.out:20（RC2=0）
python3 scripts/ohc-run.py conan-verify kma 1.4.21
#   ✅ 配方验证通过        → reports/conan-verify-report.md:3 **Verdict**: PASS（:6 Date=06:57:06.208501）

# ② finish built 的 step5 真 W3 → ~/tmp/uc2/z33-kma-fix/g4-3-finish.log:63（指明日志路径）、
#    :64（✅ W3 本地 CI 模拟通过）
python3 scripts/ohc-run.py finish kma 1.4.21 built
#   判决行在 reports/w3-local-ci.log：:23 G0_RESULT=pass、:65 KC_RESULT=pass、:92 JC_RESULT=pass、
#   :370 L0=pass、:371 L1=pass、:372 L2_RESULT=skip（框架既有形态：CI 裸跑 bin 未载 runenv，
#   不计为可执行证据）、:373 L4=pass、:374 L5=pass、:351 [result] PASS 12/12 assertions
#   ⚠ finish 整体 rc=2（未全绿），红项清单见下条第 1 项

# ③ 知识图谱自检 → ~/tmp/uc2/z33-kma-fix/g4-4-graph.log:170（✅ All checks passed (169 warnings)）；
#    整体 rc 见 ~/tmp/uc2/z33-kma-fix/g4-main.out:99（RC4=0）
python3 scripts/ohc-run.py graph validate
```

五处如实限定（不改变上述判决，只把口径说尽）：

- **finish 整体未全绿**：`~/tmp/uc2/z33-kma-fix/g4-main.out:52` 记 `RC3=2`。红项四条同源于
  `~/tmp/uc2/z33-kma-fix/g4-3-finish.log`——Step3 干净构建验证 `❌ G0: 找不到原始 tarball`
  （`g4-3-finish.log:32`，换源后本地无发行版 pool 那件 .orig 供 G0 比对，`g4-3-finish.log:33` 提示手动复核）、
  Step6 归档校验 `STEP_FAILED: Step6`（`g4-3-finish.log:122`，成因是 `g4-3-finish.log:69` 与
  `g4-3-finish.log:70` 两条「缺少 release/debug 归档压缩包」告警）、Step7 知识图谱完整性
  `❌ 发现 1 类问题`（`g4-3-finish.log:91`，同段 `g4-3-finish.log:94` 的知识完整性 self-check 为 ✅）、
  Step10 submit 就绪预检三条待建件（`g4-3-finish.log:101`、`g4-3-finish.log:102`、
  `g4-3-finish.log:103`：`reports/test-report.md`、`packaging/`、`.staging-verified`）。
  ⇒ 口径：**step5（W3）在 finish 内通过、finish 整体 rc=2**，不得把 finish 说成全绿。

- **G2 的当轮 create 日志全程 Cache 复用，但它确有测试执行段**：`reports/conan-create.log:55`、
  `:60`、`:73` 为 `- Cache`、`:65` 为 `Already installed! (1 of 1)`，且 `grep -c 'Calling build' 该件`
  实测 **0**（本轮未重新编译）；同件 **有** test_package 的执行行——`:96` `Running test()`、
  `:97` `RUN: python3 …/test_kma.py …`、`reports/conan-create.log:141` `[assert] PASS A5 kma map -mmap rc=0`、
  `reports/conan-create.log:152` `[result] PASS 12/12 assertions`。真正的本轮编译发生在 W3（`reports/w3-local-ci.log:234`
  clang 编 `trim.c`、`reports/w3-local-ci.log:247` llvm-ar 归档 `libkma.a`），
  整树从源码重编在上一棒 `~/tmp/uc2/z33-kma/create-fromscratch-r4.log:104`、`:217`。
  ⇒ 本轮「`conan create` 成功」不等于当轮重新编译过。
- **G4 与 verify 侧 L2/L4/L5 是 PASS 徽章下的空检查**：`reports/conan-verify-report.md:34-35` 的 G4
  正文唯一一行是「⚠️ 无法找到程序包 ID」，`:37-44` 的 L2/L4/L5 均为「✅ PASS」紧跟「⏭️ 跳过（无 cache 路径）」；
  同名的 L4/L5 只有 W3 侧才是真读数（`reports/w3-local-ci.log:373-374`）。G0 同理因构建系统 unknown
  跳过预查询（`conan-verify-report.md:8-10`），故 G0/G4 不给实质结论。
- 旧轮 `~/tmp/uc2/z33-kma/r3-verify.log`、`r3-w3.log`、`r3-graph.log`（mtime 04:47–04:48，早于最后一次
  功能性提交 05:51:46；`r3-w3.log` sha256 为 `c518cb44b240bd270b642515f152d8edb9bf9b891cc7db3fbd160eb26ebc059b`，
  与绑定日志的 `cb4549bc…` 不同）**不属本轮证据**，本轮不再引用，也不与 `reports/w3-local-ci.log` 互等。

- **机械件里的绝对路径属迁移前的 worktree 目录名**：`archives/k/kma/1.4.21/.ci-result.json` 第 7 行
  `archive_dir` 与 `reports/conan-create.log:97` 的 RUN 行都写作
  `/storage/Users/currentUser/qzy/主理-33-kma-1.4.21/archives/k/kma/1.4.21`，而盘上现存目录是
  `~/qzy/主理-43-kma-1.4.21/archives/k/kma/1.4.21`。成因：这两件产自主理-33 时期的**同一次运行**，
  之后该 worktree 按规则**无损 move** 到本窗名下（`git worktree move`，规则内动作），机械件因此留下
  旧绝对路径。⇒ **本轮不手改 `.ci-result.json`**（一改就破坏它与 `log_sha256` = `cb4549bc…` 的绑定），
  机械件未改、sha 绑定仍有效；读该字段时按「目录名换过、内容未变」理解，路径末段
  `archives/k/kma/1.4.21` 与归档实际相对路径逐字一致（同见第 5 轮独立 W4 判决件 P2-1）。

消费者测试关键实测读数（本轮 W3 绑定日志 `archives/k/kma/1.4.21/reports/w3-local-ci.log`；`kma -v` 见 `reports/w3-local-ci.log:302-303`、`kma index` 见 `reports/w3-local-ci.log:319-322`、`kma -mmap` 比对见 `reports/w3-local-ci.log:339-350`、合计 `reports/w3-local-ci.log:351`）：
`kma -v` → `KMA-1.4.21` rc=0；`kma index` rc=0 且 `testdb.comp.b` size=4208420（>1 MiB 真实压缩库）、
`testdb.length.b` size=20；`kma -i query.fa -t_db testdb -mmap` rc=0；`.res` 数据行 1 行，
`t1 / Score 300 / Query_Identity 100.00 / Template_length 600 / Template_Coverage 50.00 /
Query_Coverage 200.00`；`.aln` 头 `# t1`，5 段 60 连 `|` 全匹配 + 5 段 60 连 `_` 未覆盖。

## 测试账本（五维，与 test_package/MANIFEST.yml、manifest.yaml 同源）

| 维度 | 数值 | 口径与证据 |
|---|---|---|
| `N_static`（上游静态注册用例） | 0 | 手工清点，**未用** `ci/tools/extract_upstream_tests.sh`（该脚本硬编码读 `/tmp`，本设备必失败，其 log 不能当证据）。证据：`~/tmp/uc2/z33-kma/inventory-report.txt`、`inventory/`、`inventory.sh`、`index2.log`。读数：Makefile 目标行 63 条（`all/kma/kma_index/kma_shm/kma_update/libkma.a/clean` 真目标 + 56 条 `.o` 依赖声明），`grep -nE '^(check\|test\|install)' Makefile` 0 命中，`make -n check` rc=2，tar 154 条目中 `test\|spec\|check` 文件名命中 3 条且全为巧合（`KMAspecification.pdf`、`qualcheck.c/h`），跨框架注册 grep 0 命中，`t/tests/test/spec` 目录 0 个，上游 CI（4 份 workflow + bitbucket-pipelines.yml）测试步骤 0 条，`performanceAndComparisonCMDs.tar.gz` 5 条目属基准资产非注册测试 |
| `N_registered`（构建系统注册的可执行测试目标） | 0 | 同上：Makefile 无 check/test 目标可注册 |
| `N_executed`（实际执行的上游用例） | 0 | 分母为空，属"上游确无测试可集成"，不是"有而不执行"；配方 `build()` 因此未挂上游测试（`manifest.yaml: upstream_tests: 0`、`upstream_test_in_build: false`） |
| 未执行分类数（跳过/预期失败/资源缺失） | 0 | 无上游用例可分类；W3 的 `L2_RESULT=skip` 是框架冒烟矩阵形态，不并入本维度 |
| `N_consumer`（新增消费者测试） | 12 | 数值列只放整数：12 条断言 A1–A12，本轮实测 12/12 PASS。载体是 **1 个**消费者程序 `test_package/test_kma.py`（真实端到端：产物建库 + `-mmap` 真比对 + 逐字段核对数值），一手判决 `reports/w3-local-ci.log:351` `[result] PASS 12/12 assertions`；12 这个数字三处同源同为 12：`reports/w3-local-ci.log:351`、`archives/k/kma/1.4.21/manifest.yaml:70`、`archives/k/kma/1.4.21/test_package/MANIFEST.yml:65` |

统计（与 PR 正文口径一致，逐维均为纯整数）：上游 发现 0、执行 0、通过 0、失败 0、跳过 0；
消费者测试 发现 12、执行 12、通过 12、失败 0、跳过 0；合计（上游与消费者逐维相加）发现 12、
执行 12、通过 12、失败 0、跳过 0。与 `N_static` 的大小关系另句说明、不占数值位：合计执行 12
不小于 `N_static` 0，分母未缩（上游确无可注册用例，属「上游无测试可集成」，不是「有而不执行」）。

## 交付物

| 文件 | 大小（字节） | 说明 |
|------|------|------|
| `bin/kma` | 571904 | 主程序（map/index/db/dist/shm 等子命令；本平台比对须加 `-mmap`） |
| `bin/kma_index` | 186880 | 建模板库（实测 rc=0，产物 `testdb.comp.b` 4208420 字节） |
| `bin/kma_shm` | 35200 | SysV 共享内存常驻服务端，本平台不可用（见注意事项） |
| `bin/kma_update` | 31104 | 模板库增量更新 |

本表四行是**构建产物**（本轮无构建、`conanfile.py` 与 `conandata.yml` 零改动）；四件字节数按本次
整改当日 `ls -l ~/tmp/ch/home-kma/p/b/kma081b916ca359d/p/bin/` 复测，与表内逐字一致：`kma` 571904、
`kma_index` 186880、`kma_shm` 35200、`kma_update` 31104。

**本 PR 的仓内交付物（第 6 轮 W4 的 P2-3 定案「证据件随 PR」后重算，全部 `wc -c`／`wc -l` 实测）**：
`git ls-files archives/k/kma/` 现为 **16** 件——原 12 件配方与文档之外，本棒用 `git add -f` 把 notes 与
README 按行号引用的三份运行日志、连同第 6 轮独立 W4 判决件一并提进本 PR：
`1.4.21/reports/w3-local-ci.log`（384 行、25930 字节）、`reports/conan-create.log`（153 行、7507 字节）、
`reports/conan-verify-report.md`（44 行、1074 字节）、`reports/audit-result.json`（140 行、29021 字节）。
`.ci-result.json` **不随 PR**——取舍按 `upstream/main` 实测口径定案（`conan-verify-report.md` 173 份归档已
跟踪、`conan-create.log` 32、`w3-local-ci.log` 19，而 `.ci-result.json` 全仓 0 份），带件要解决的是本 PR
可见文本里 55 处 `reports/…:NNN` 形式的行号锚（notes 42 / README 9 / 版本级 manifest 4）在评审侧解析不了。
另两枚知识交付物：`knowledge/drafts/DRAFT-kma-1.4.21-unconditional-sysv-probe-makes-upstream-file-fallback-unreachable-and-wall-is-per-subcommand.kv`
= **21447 字节**、同名 `.md` = **15617 字节**（本轮按 P2-1/P2-2/P3-4/P3-5 改文后重测）⇒ PR diff 共
**18** 个文件（`archives/k/kma/**` 16 ＋ `knowledge/drafts/` 2），无第三个包、无框架件；
`conanfile.py`、`conandata.yml`、`.ci-result.json` 本轮零改动 ⇒ recipe revision 不变。

## 注意事项（本平台功能面披露，如实陈述）

以下三条在本平台**不可用**，均因默认路径必经 SysV shm（详见问题表 #1）：

1. `kma map`（即 `kma -i <query> -t_db <db>`）不加 `-mmap` 时 rc=159，四个输出文件全 0 字节；
   加 `-mmap` 后 rc=0 且结果正确 ⇒ **本平台使用方式必须带 `-mmap`**。
2. `kma db -t_db <db>`（直接对 SysV 中的库做比对）rc=159。
3. `kma shm`（常驻共享内存服务）整条依赖 SysV shm，本平台不可用（本项**未实跑**该子命令：依据是 syscall 探针 `~/tmp/uc2/z33-kma/probe-summary.txt:5` 的 shmget/shmat 击杀读数，与 `shm.c` 是唯一 `IPC_CREAT` 建立方的源码事实）。

可用面（有 rc=0 与产物读数）只有 `kma -v`、`kma index`、`kma -mmap` 比对三项；`kma dist`、`kma trim`、`kma seq2fasta`、`kma -h`、`kma update` 一律按未测登记（无功能读数，不得当成可用）；`kma map` 默认路径、`kma db`、`kma shm` 为不可用。
逐子命令一手读数（本轮全部按 `reports/w3-local-ci.log` 当前 384 行逐行复算；每条锚前重复写全被引件名，便于机器对字）：`kma -v` = `reports/w3-local-ci.log:302`（`[run] rc=0`）+ `reports/w3-local-ci.log:303`（A1 `out='KMA-1.4.21'`）；`kma index` = `reports/w3-local-ci.log:319`（`[run] rc=0 (lines=19)`）、`:320` A2、`:321` A3（`testdb.comp.b` size=4208420）、`:322` A4（`testdb.length.b` size=20）；`kma -mmap` 比对 = `reports/w3-local-ci.log:339`（`[run] rc=0 (lines=23)`）、`:340` A5、`:342` A6、`:344`–`:348` A7–A11、`:349` A12、`:350`（`out_mmap.fsa: 309 bytes`），合计 `reports/w3-local-ci.log:351`（`[result] PASS 12/12 assertions`）。`kma dist` = `~/tmp/uc2/z33-kma/steps.log:43` `dist_rc=1` 配 `dist.log:1` `Invalid value parsed at "-d".`（首轮用法写错，`STATE.md:67` 自记）与 0 字节的 `distB.log`（其 rc=0 只见于 `STATE.md:35`、`:71` 的自述）⇒ 未测。`kma trim` = 现存日志只有编译与归档行 `reports/w3-local-ci.log:234`（clang `-c -o trim.o trim.c`）与 `reports/w3-local-ci.log:247`（`llvm-ar -csr libkma.a …trim.o…`）⇒ 未测。`kma seq2fasta` = `steps.log:42` rc=1 且 `s2f.log:1-5`、`s2fB.log:1-5` 全文只有 usage 页 ⇒ 未测。`kma -h` = 无单独实跑留痕，绑定日志 `reports/w3-local-ci.log:365` 的 `kma --version/--help failed` 属 W3 L2 冒烟的双横线形态 ⇒ 未测。
（本行行锚按换源重跑后的 `reports/w3-local-ci.log` 全文 384 行逐行复核；`reports/w3-local-ci.log:355` 现为 `[ok] L1a` 行、`reports/w3-local-ci.log:365` 为 L2 对 `kma --version/--help` 的 warn 行、五值判决行在 `:370`（L0）`:371`（L1）`:372`（L2_RESULT=skip）`:373`（L4）`:374`（L5））不适用面（不得当成通过）：任何走默认 SysV 哈希表的调用。

未实测面（不得当成可用）：`kma update`。第 4 轮独立审计判明：先前那两件日志
（`~/tmp/uc2/z33-kma-fix/up-bare.log` 41 字节、`~/tmp/uc2/z33-kma-fix/up-i.log` 338 字节，
05:24 落盘）**只落了 stdout、全件内 `rc=` 0 命中**，⇒ 当时那两个 rc 数字缺一手载体。
本轮 08:44 用同一枚已交付产物（`~/tmp/ch/home-kma/p/b/kma081b916ca359d/p/bin/kma`，即
`reports/w3-local-ci.log:297`、`:298` 所记的 571904 字节件）补跑两式，日志按
「命令行 / rc / stdout 原文」三段落盘：
`~/tmp/uc2/z33-kma-fix2/up2-bare.log:2` = `rc=0`、`:4` = `Insuffient amount of arguments
handed!!!`（上游原文拼写如此，缺两个 e）；`~/tmp/uc2/z33-kma-fix2/up2-i.log:2` = `rc=1`、
`:4` = `Invalid option:` 后跟制表符与 `-i`、`:6` 起是
`# KMA_update synchronises kma-indexes to the needed version.` 的帮助页
⇒ 未试出正确用法、**没有任何功能读数**（`update.c` 里 `shmget` 计数 0 属静态推测，推测不得写成
已测结论）。`rc=0` 同样不是可用证据：无参那式只走到 usage 打印即返回，未触碰任何库读写。
⇒ 该子命令既不入"可用面"也不入"不可用面"，只登记为未测。

## 适配过程记录

### 对话 #1 [2026-09-25]（第一棒：能力墙定位）

- 问题: 默认比对路径退出码 159（128+31=SIGSYS）、`out_default.*` 四件全 0 字节，`kma db -t_db` 同症状
- 操作: 逐 syscall 号探针（`probe.c` / `probe-summary.txt`）+ 读上游哈希表实现定位到 `hashmapkma.c:319/349/385/416` 的 `ftok`+`shmget`；再翻上游帮助文本找到自带的 `-mmap` 后端（`kma.c:144`、`kma.c:525-527`、`kmers.c:86-87`、`sparse.c:381-382`、`kmmap.c:33`）
- 结果: 定性为平台 seccomp-BPF 按 syscall 号击杀 SysV IPC；`kma index` rc=0（建库 stdout 见 `~/tmp/uc2/z33-kma/index2.log:1-19`、产物 `testdb.comp.b` 4208420 字节；**该件只落 stdout，rc 数字的一手载体是台账 `~/tmp/uc2/z33-kma/STATE.md:69`**）、加 `-mmap` 的比对 rc=0（stdout 见 `~/tmp/uc2/z33-kma/runB.log:1-23` 与 `out_mmap.res` 给 `t1 Score 300 Query_Identity 100.00`；**rc 同上记于 `STATE.md:70`**）；同一批读数在当前绑定日志里另有一手 `rc=0` 行：`reports/w3-local-ci.log:319`（index）与 `reports/w3-local-ci.log:339`（`-mmap` 比对）。默认路径与 `kma db` 分别以 `runA.log:8`、`dbB.log:2` 的 `Signal 31 (core dumped)` 收场 ⇒ 走路径 A，不改上游。该轮对 `kma dist`/`kma seq2fasta` 的实跑把选项写错（`steps.log:42-43` 均 rc=1），不构成子命令能力读数 ⇒ 二者本轮按未测登记（见注意事项）

### 对话 #2 [2026-09-25]（第二棒：配方与消费者测试）

- 问题: `conan create` 的 test_package 工作目录取 `os.getcwd()`，产物会落进 `test_package/`（设备 `/tmp` 只读、root `.gitignore` 未覆盖这些输出名）
- 操作: 改为在 `$TMPDIR`（缺省退 `~/tmp`）下 `tempfile.mkdtemp(prefix="kma-consumer-")` 开唯一子目录
- 结果: 消费者测试 12 条断言在 `conan create` 内真实执行并通过；当前绑定 W3 日志的实测工作目录为 `/storage/Users/currentUser/tmp/kma-consumer-31fwb74y`（`reports/w3-local-ci.log:296`、`reports/w3-local-ci.log:299`；mkdtemp 后缀每轮不同，换源前那轮的 `h3vsbau5` 已不可引用）

### 对话 #3 [2026-09-25]（第三棒：按当时 HEAD 复跑门禁；该轮日志前缀 `r2-`，05:52–05:54，已被对话 #4 的换源重跑取代）

- 问题: 上一棒的改动未提交，旧 verify/W3 日志不可充数
- 操作: 先提交工作目录改造，再依次复跑 `conan-verify`、`finish built`（step5 跑 `ci/conan/build_and_test.sh`）、`graph validate`，日志落 `~/tmp/uc2/z33-kma-fix/r2-verify.log`、`r2-finish.log`、`r2-graph.log`（05:52–05:54）；此前两跑的 `~/tmp/uc2/z33-kma/r3*.log` 早于该轮最后功能性提交 05:51:46，不作该轮证据。**注意**：该轮写下的 `reports/w3-local-ci.log` 已被下一轮（对话 #4）覆盖 ⇒ 下列三件 `r2-*` 日志本身仍在盘上可查，但其中引用的 w3 行号一律以当前件为准
- 结果: 该轮 `conan-verify` 通过（`~/tmp/uc2/z33-kma-fix/r2-verify.log:19` 是该件的判决行「✅ 配方验证通过」；该件内**没有** `VERIFY_RC=` 落盘行，rc 数字的载体是驱动件，当前轮为 `~/tmp/uc2/z33-kma-fix/g4-main.out:20` 的 `RC2=0`）且 `reports/conan-verify-report.md:3` 的 `**Verdict**: PASS`，其中 G1/G2/G3 为实质 PASS，G0 因构建系统 unknown 跳过预查询（`reports/conan-verify-report.md:8-10`）、G4 找不到程序包 ID 而空跑（`reports/conan-verify-report.md:34-35`），verify 侧 L2/L4/L5 亦为「跳过（无 cache 路径）」（`reports/conan-verify-report.md:37-44`）；该轮 W3 一次通过，`exit_code: 0` + `[result] PASS 12/12 assertions`（`r2-finish.log:62`；同一行在当前绑定日志里是 `reports/w3-local-ci.log:351`），且该轮 `reports/conan-create.log` 全程 Cache 命中（`:55`、`:60`、`:65`、`:73`）、真实编译在 W3 日志内（当前件行号 `reports/w3-local-ci.log:234`、`reports/w3-local-ci.log:247`）；`~/tmp/uc2/z33-kma-fix/r2-graph.log:170` 为该轮的图谱自检判决行（169 warnings 属存量；该件内同样**没有** `GRAPH_RC=` 落盘行，rc 载体是驱动件，当前轮为 `g4-main.out:99` 的 `RC4=0`）

### 对话 #4 [2026-09-25]（第四棒：取源换向上游 tag 归档、门禁重跑、对外账面复算）

- 问题: preflight PF7/R39（`scripts/ohc/preflight.py` 的 `check_source_urls`）无条件把
  `deb.debian.org` 判作下游重打包源，而建 PR 前的闸门 fail-closed ⇒ 两份归档逐文件等价也过不了闸
  （取证过程与等价性复算见「源码获取」节）
- 操作: `conandata.yml` 与 `conanfile.py` 改指 `https://bitbucket.org/genomicepidemiology/kma/get/1.4.21.tar.gz`
  （落盘为提交 `936ceeb2dd`，07:00:09），随后按新配方复跑 `conan-verify`、`finish built`、
  `graph validate`，日志前缀 `g4-`（06:56–06:57）；W3 重跑覆盖 `reports/w3-local-ci.log` ⇒ 当前件 384 行、
  sha256 `cb4549bc…`，**换源后所有 `:NNN` 锚都发生位移**
- 结果: 三值同「验证结果」节的 `g4-*` 锚（`~/tmp/uc2/z33-kma-fix/g4-main.out:20` = `RC2=0`、
  `:52` = `RC3=2`、`:99` = `RC4=0`）；W3 判决 `reports/w3-local-ci.log:351` 为 `[result] PASS 12/12 assertions`、
  五值判决在 `reports/w3-local-ci.log:370`-`reports/w3-local-ci.log:374`。第 4 轮独立审计判
  「不可，必须先改」后，本轮另写**只读**行锚扫描脚本，把包目录内 12 个受版本控文件里的
  每一条 `:NNN` / `:NNN-NNN` / 「第 N-M 行」锚与被引对象的真实行内容逐条对字，
  改前清单 `~/tmp/uc2/z33-kma-fix2/anchor-scan-before.txt`（35456 字节）、改后复跑清单
  `~/tmp/uc2/z33-kma-fix2/check-after.txt`（56446 字节；同一脚本 `anchor_expect.py`、同一真值表
  `keys.txt`）。⚠ 该次扫描面只含包目录 12 件、**不含本 PR 的 `knowledge/drafts/` 两枚草稿** ⇒ 下面这条
  是**扩面前**的数，不得当最新全量（扩面复算见对话 #6）。汇总行原文（`check-after.txt:290`，扩面前）：「=== 汇总 OK=287 MISMATCH=1 UNCOVERED=0
  BROKEN=0 IGNORED=1 锚点合计=288 ===」；配套在盘件另有两枚——锚点库 `scan-after-inventory.txt`
  （52461 字节）、改前对账 `check-before.txt`（46654 字节）。唯一那条 MISMATCH（`check-after.txt:266`，
  README:55 引 `w3-local-ci.log:344-348` 表示 A7–A11）经第 5 轮独立审计一手复核确认是扫描器把
  区间起点标签错配成 A5 的**假阳性**（实测 340 为 A5、344 为 A7、348 为 A11），文档与日志一致；
  其余 287 条逐字对中。
  提交信息称「行锚全量复算」而实只改了 notes 的四批，本轮把 README/manifest 与 notes 其余各批一并补齐

### 对话 #5 [2026-09-25]（第 5 轮独立 W4 的两条 P1 与两条 P2 整改：B 判定 hit → create）

- 问题: 第 5 轮独立 W4 判决件 `~/tmp/uc2/z43-kma-audit5/audit-result.json`（124 行、19260 字节，
  sha256 `0ec044fdfe236b92fb406d8909ef3e65e68dd42f1d6e91a9d0fec7e09d524a6b`，`audited_commit`
  = 本轮开工 HEAD `06a1d1a5cc3e61b87b4cba13f26212610283682b`）判 `verdict: fail`，计数
  P0=0 / P1=2 / P2=2 / P3=3
- 操作: ①**P1-1**：按主理定案把 B 判定由 hit 改判 **create**（判据 = `经验文档/手册/03-路径B与C.md:82-83`
  两条前置都不满足），成对草稿从 **git** 取回本 PR 的 `knowledge/drafts/`——取物命令
  `git show db9b807a42:knowledge/drafts/DRAFT-kma-1.4.21-<slug>.{kv,md}`（判决件与本文件旧台账写的
  `554dc4815ec5b3fe239d1110838c1ec5852f07c0` 那一枚**树内没有这对草稿**，`git show` 实测 rc=128；
  草稿实际成立于 `db9b807a42`，被 `3fd3508a07` 撤出 ⇒ 本轮按 git 版取回，未从
  `~/tmp/uc2/z33-kma-fix/pool-export/` 复制），并改掉三处过期表述（`.kv` 的 `source_commit`、
  `.md` 第六节的定案措辞、`.kv` 头注）、把查重段改为按文件名逐份点名三份池内草稿；
  ②Issue **#3402** 由主理创建并回填号（见下面 3+2 的关联 Issue 行）；③**P1-2**：改后清单锚改为
  盘上实存的 `~/tmp/uc2/z33-kma-fix2/check-after.txt` 并复述其 `:290` 汇总行原文；④**P2-1**：补
  worktree move 说明，**不手改** `.ci-result.json`（保 `log_sha256` 绑定）；⑤**P2-2**：五维表
  `N_consumer` 数值列与合计行改纯整数、解释移入口径列与正文
- 结果: 本轮**零构建**（配方两件 0 改动 ⇒ rrev 不变），只读复算三件全中——
  `draft-review` rc=0：质量预检 `signature=✅ root_cause=✅ rec=✅`
  （`~/tmp/uc2/z43-kma-fix3/draft-review-r6.log:3`）、TOP3 = E051 0.21 / E246 0.21 / E338 0.19
  （同件 :6、:10、:13）、**预审建议 create**（:16）⇒ 无 merge-into；
  `knowledge_check.sh <仓根>` ⇒ `KC_RESULT=pass`、`KC_ERRORS=0`
  （`~/tmp/uc2/z43-kma-fix3/knowledge-check-r6b.log:24-25`；首跑误传包路径得到的
  `KC_RESULT=pass: no_graph` 属参数用错的空过，已弃用）；
  `graph validate` ⇒ rc=0、`~/tmp/uc2/z43-kma-fix3/graph-validate-r6.log:170`
  「✅ All checks passed (169 warnings)」⇒ 警告数与既存基线 169 同数。三条 P3（P3-1 读数注记、
  P3-2 扫描器标签缺陷、P3-3 tmp 目录命名）**不在本轮交办范围**，未顺手改动

### 对话 #6 [2026-09-25]（第 6 轮独立 W4 的 3 条 P2 与 3 条可机械修的 P3：提审前收尾）

- 问题: 第 6 轮独立 W4 判决件（开工时读设备侧 `~/tmp/uc2/z43-kma-audit6/audit-result.json`，本棒按
  P2-3 随 PR 入档为 `1.4.21/reports/audit-result.json`＝140 行 29021 字节，与本棒读到的权威件逐字节
  相同）判 `verdict: pass`、P0=0 / P1=0 / P2=3 / P3=6，其 `audited_commit` 与本棒开工 HEAD 同为
  `c15ff8a01c1f5480ae1d81b2f0102b31810b5376`
- 操作: ①**P2-1** 草稿 `.md` 的 `kma update` 依据列换载体——原引 `~/tmp/uc2/z33-kma-fix` 目录里的
  `up-bare.log`（41 字节）与 `up-i.log`（338 字节）实测全件内无 `rc=` 行、只落 stdout ⇒ 那两个 rc 当时
  缺一手载体；现按 README 同一口径改引 `~/tmp/uc2/z33-kma-fix2/up2-bare.log` 的 rc 行（`rc=0`，其 `:4`
  为 usage 原文）与 `up2-i.log` 的 rc 行（`rc=1`，再往下是 `Invalid option:` 与帮助页），旧两件在草稿
  「证据件」节保留但改记为「不构成 rc 载体」；②**P2-2** 新增锚重算后改对：
  `knowledge-check-r6b.log` 的 `KC_RESULT=pass` 实测在该件倒数第二行、`KC_ERRORS=0` 在末行（草稿与下面
  对话 #5 原写的两行号其实落在分隔线与 `Errors: 0` 上）；`draft-review-r6.log` 的「疑似新知——无高相似
  条目，可考虑人工审核后纳入」在「📌 预审建议: create」的**下一行**，草稿原来把原文挂在建议行名下 ⇒
  已改为「建议行 + 原文在下一行」的写法，本文件对话 #5 那处行号同步改对。锚扫描器覆盖面由「包目录 12 件」
  扩到**再加本 PR 的 `knowledge/drafts/` 两枚草稿**（脚本 `anchor_scan.py` 的 `tracked_files()` 现同时收
  `.md` 与 `.kv`，本棒副本与产物在 `~/tmp/uc2/z43-kma-close/`），并把与本轮整改同源的 17 条锚编进
  `anchor_expect.py` 真值表（12 条按「被引件＋锚原文」定位、5 条按引用方行号精确定位），其中新加的
  「`kma.c` 第 525 行必须同时含 `-mmap` 与 `-swap`」与「`probe-summary.txt` 汇总行必须列全八个号」两条
  判据就是防 P3-4/P3-5 复发的；③**P2-3** 证据件随 PR（件数与字节数见「交付物」节），并把对话 #4 那条
  旧汇总行显式标为**扩面前**的数；④**P3-4** 三处以「原文」名义截断 `kma.c` 第 525 行的地方（草稿第一节、
  草稿能力三态表、本文件 3+2 的「使用知识库」行）补全为含 `strcmp` 两支的整条判断，并在解法面点明
  `-swap` 与 `-mmap` 命中同一分支、效果相同；⑤**P3-5** 草稿被拦 syscall 行按一手件
  `~/tmp/uc2/z33-kma/probe-summary.txt` 汇总行列全八号（补 `msgsnd`/`msgrcv`/`semop`，与同名 `.kv`
  口径同源），并如实标注 radioclk 侧探针只覆盖其中 `shmget`/`shmat`/`shmdt`/`msgget`/`semget` 五号
  （`~/tmp/uc2/z33-radioclk/shm-probe-run3.log` 内没有 msgsnd/msgrcv/semop 三条）；
  ⑥**P3-6** 台账用词订正：对话 #5 那条提交 `7b6eaa726c` 所称「软件级 manifest」实为**版本级**
  `archives/k/kma/1.4.21/manifest.yaml`——`knowledge_gained` 只存在于版本级 manifest；软件级
  `archives/k/kma/manifest.yaml` 全文 7 行、不含该字段、本轮未动 ⇒ 三载体同步本身没有缺口，
  本棒不为此改软件级 manifest 的内容
- 未做: 第 6 轮的另两条 P3（P3-1 README 表前的「换源前读数」注记、P3-2 扫描器对区间起点标签的绑定缺陷）
  不在本棒交办范围，如实留着。下面汇总行里的 MISMATCH 就是对话 #4 已一手复核的那条区间起点假阳性；
  BROKEN 全部与本棒新写的 reports 日志锚无关，同属扫描器把行号绑到「同句里最近的另一个文件名」的绑定缺陷
  （不是正文写错）——本棒把每条 BROKEN 的**被引对象**都按真实文件与真实行逐条对字复核过，结论落在扫描产物
  同目录的 `broken-triage.txt`（设备侧件，刻意不写进 PR 可见文本，以免在仓内再制造一批同类误绑锚）；
  UNCOVERED 是**尚未编入真值表的存量锚**（扫描器只登记、不判红），本棒只补了与本轮整改同源的那 17 条
- 结果: 本轮**零构建**，`conanfile.py`、`conandata.yml`、`.ci-result.json` 零改动 ⇒ 绑定在
  `kma/1.4.21@ohpcd/stable#8e0b36e9f5ad8a6431703b5f31993dd9` 上的 W3 与 verify 证据继续有效。
  扩面后复算的锚点汇总行原文（`~/tmp/uc2/z43-kma-close/check-summary-r7.txt` 首行，逐条清单是同目录的
  `check-after-r7.txt`）：「=== 汇总 OK=348 MISMATCH=1 UNCOVERED=77 BROKEN=5 IGNORED=1 锚点合计=431 ===」——锚点合计从对话 #4 那次的 288 涨到本轮读数，增量来自
  `knowledge/drafts/` 两枚草稿进入扫描面、以及 reports 四件随 PR 后新增的行号级引用

## 路径与知识库声明（3+2）

- 适配路径: A（直接适配，零补丁；`-mmap` 是上游自带的运行方式，不改上游换 POSIX shm、不 vendor 假 shm 层、不加 stub、不缩分母、不把 skip 说成通过）
- 使用知识库: **create（本 PR 携带成对新建知识草稿；机制层挂靠池内既有条目、不重申报）**。改判依据（第 5 轮独立 W4 的 P1-1，主理已定案）：`经验文档/手册/03-路径B与C.md:82-83` 两条前置本包**都不满足**——① 条目外新行为偏差：池内「DRAFT-ohos-sysv-shmget-sigsys」第 22 行写「拦截 shmget/shmat/shmctl」，而本包（`~/tmp/uc2/z33-kma/probe-summary.txt`）与 radioclk（`~/tmp/uc2/sysv-shm-probe/probe_sysv_shm2.c`，判决 `~/tmp/uc2/z33-radioclk/shm-probe-run3.log`）两侧独立探针实测 `shmctl`/`msgctl`/`semctl` 进内核返 EINVAL(22)＝**放行**、`ftok` 放行、POSIX shm 与文件 mmap 对照组全通过；② 既有条目没写的另一条解法：该条第 36-38 行是**编译期** mmap 开关（`fallback_approach: compile-time-mmap-switch`）、第 39-45 行是手工重写换 POSIX shm，而本包零补丁、不换后端，用上游自带的**运行期 argv 开关** `-mmap`（`kma.c:525` 原文 `else if(strcmp(argv[args], "-mmap") == 0 || strcmp(argv[args], "-swap") == 0)`、:526 置 `shm |= 32`、:527 换 `hashMapKMA_munmap`；同一行右半支 `-swap` 与 `-mmap` 命中同一分支、效果相同）⇒ 按 `手册/03:83`「多一条可选路径 + 它的适用面与代价本身就是可复用知识」应为 create。机器面如实披露：verify 的 G0 预查询对本包报「构建系统 unknown ⇒ 跳过预查询」，故 G0 对 B 判定不构成任何结论。人工挂靠面按**文件名**逐份点名（「knowledge/drafts/ 里 E 编号被复用」⇒ 一律不挂 E 号）：机制本体 =「DRAFT-ohos-sysv-shmget-sigsys」第 20-24 行根因段（本包不重申报）；errno 回退一般结论 =「DRAFT-E577-buffer-sysv-ipc-posix」第 23-27、31-36、38-44 行；按入口分列的台账形态 =「DRAFT-E584-bus-sysv-ipc-sigsys-catchable」第 51-60、62-72 行（该件全文 93 行内**没有**「按子命令/API 面点名披露」这句规则——按 点名/披露/可用面/子命令/按入口 五个关键词 grep 0 命中，本包只借其分列形态并把判据显式化）；解法类型 =「knowledge/doc/E237.md」第 26 行方法名与第 28 行「编译验证 + 运行期降级/shim 三选一」（路由桥是同包第 79 行分流句），其三个选项都以「运行期无可用事件源」为前提、未逐字覆盖「零补丁 + 上游自带 argv 开关把功能真跑通」这一形态。**上一版 3+2 里「其第 1 条覆盖本包解法」与「维持 hit」两句超出覆盖面的表述已删除**；本轮复跑的工具判决与两枚草稿的路径、字节数见「知识库扩展」行与「交付物」节
- 知识库扩展: **create —— 新增条目（成对草稿随本 PR 原子提交，路径与实测字节数见「交付物」节）**：`knowledge/drafts/DRAFT-kma-1.4.21-unconditional-sysv-probe-makes-upstream-file-fallback-unreachable-and-wall-is-per-subcommand.md` 与同名 `.kv`。新增的是既有条目都没有的**三条组合层内容**：①「上游无条件 SysV 探测使 else 文件回退不可达」这一**探测型结构判据**（进入条件是被拦调用的**返回值**还是被拦调用**本身**；后者在 SECCOMP_RET_TRAP/KILL 下恒不可达，并给出 `hashmapkma.c:27-36` 的 `#ifdef _WIN32` 恒失败桩宏作对照）；②「同一道能力墙按子命令分面」的**分布读数**（`kma map` 默认不可用 rc=159 / 带 `-mmap` 可用 rc=0、`kma db` 与 `kma shm` 无出路，依据 `grep -rl` 位掩码全树只命中 kmers.c 与 sparse.c）；③**上游自带运行期 argv 开关**这条既有条目没写的解法及其适用面与代价。查重逐份点名（按文件名）：「DRAFT-ohos-sysv-shmget-sigsys」= 机制本体 + 编译期开关 + 手工换 POSIX shm，不含上述三条 ⇒ 本包挂靠它、不重申报机制；「DRAFT-E577-buffer-sysv-ipc-posix」= 一般结论与旁证清单，无读码判据、无平台桩宏对照；「DRAFT-E584-bus-sysv-ipc-sigsys-catchable」= 隐含的分列台账与分流决策，无显式按子命令点名披露判据。组合型知识不判重（`经验文档/手册/03-路径B与C.md:89`）：组分清单 = 上述三件已写内容，组合后新增 = 一条静态读码判据 + 一条按子命令披露判据 + 一条运行期开关解法。条目外偏差随本条**提请修正**池内条目、不代改：「DRAFT-ohos-sysv-shmget-sigsys」第 22 行「拦截 shmget/shmat/shmctl」的 `shmctl` 半句已被两侧独立探针否证 ⇒ 建议改为「创建/挂接类被拦、控制类 `*ctl` 放行」。另**提请条目所有者裁定**池内互斥：「DRAFT-E584-bus-sysv-ipc-sigsys-catchable」第 1 行标题与第 28-29 行称 SIGSYS 可捕获，与「DRAFT-ohos-sysv-shmget-sigsys」第 47 行「不可捕获，方案无效」、「DRAFT-E577-buffer-sysv-ipc-posix」第 36 行「通常不可恢复」互相排斥 ⇒ 本包读数（命中 shmget 后 rc=159 终止、未捕获未续跑）只支持"该进程未捕获"这一事实面，不据任何一方定性。关联 Issue 见下一行；本轮复跑的工具判决行原文见「适配过程记录」对话 #5 与草稿 `.md` 第六节
- 关联 Issue: **#3402**（B=create 的知识库扩展 Issue，随本轮整改回填）——标题「【知识库扩展】kma 1.4.21：无条件 SysV 探测使按 errno 的文件回退分支成死路，首选上游自带运行期 -mmap 开关（零补丁）」，绝对链接 https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3402 ，由主理创建并回填号，回填时基线 HEAD `06a1d1a5cc3e61b87b4cba13f26212610283682b`（本轮整改的开工 HEAD，与第 5 轮独立 W4 的 `audited_commit` 同一枚）。本行取代上一版「无需新建（B=hit）」那句已过期的结论
---

**编译结束**: 2026-09-25 06:57
**最终状态**: built
