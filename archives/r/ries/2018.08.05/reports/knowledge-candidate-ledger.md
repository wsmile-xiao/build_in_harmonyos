# ries 2018.08.05 知识候选台账（路径 B 判定）

判定工具与范围：本包实测探针 + worktree `knowledge/graph/`、`knowledge/doc/`、
`knowledge/operations/`、`knowledge/drafts/`（**含手工 `git grep -i` 扫 `knowledge/drafts/`，
因 `draft-review` 工具不扫该目录**）+ 仓内 prescan/规则件 + `archives/*/*/notes.md` 归档先例。
判据：`经验文档/手册/03-路径B与C.md` 第 80-90 行"家族命中判 hit 的四条件"。

---

## 候选 1：上游 `install` 目标调用宿主 `install(1)`，OHOS worker 无该程序

**本包症状（一手探针）**

```
$ make -f GNUmakefile install DESTDIR=$HOME/tmp/uc2/z45-ries/stage PREFIX=/usr
mkdir -p .../stage/usr/bin .../stage/usr/share/man/man1
install -m 0755 ries   .../stage/usr/bin
make: install: No such file or directory
make: *** [GNUmakefile:18: install] Error 127
INSTALL_RC=2
```

探针件：`~/tmp/uc2/z45-ries/m2.sh`（39 行，含取源/编译/试装/冒烟）与
`~/tmp/uc2/z45-ries/logs/manual-install.log`、`logs/manual-make.log`；判据目标全集见
`m5.sh` / `logs` 的 R51 清点节。探针不含任何三方库代码。

> 口径补充（第 3 棒）：本节 :23-24 与候选 2 末行引用的第 1 棒探针件与 `logs/` 目录同在设备可丢弃区、未随 PR；其**结论性读数已在本文件内照录**（即上面的探针输出代码块），需重建取证时按 notes.md 的 A1/A3 节口径重跑即可。

**四范围查重（精确到行）**

| 范围 | 命中件与行号 | 内容 |
|---|---|---|
| graph 正式条目 | `knowledge/graph/E174.kv:5` | `error_signature: make: install: No such file or directory\|install: command not found\|make\\[\\d+\\]: install: No such file or directory` —— **与本包首条真实错误逐字一致** |
| 同上 | `knowledge/graph/E174.kv:13` | `root_cause: OpenHarmony 缺少 GNU coreutils 的 install 命令。` |
| 同上 | `knowledge/graph/E174.kv:17` | `affected_scope: 使用 Makefile install 目标的项目，依赖 install 命令的安装脚本` |
| 同上 | `knowledge/graph/E174.kv:22-23` | `rec_approach: manual-install` / `rec_description: 手动使用 cp + chmod 替代 install 命令进行文件安装` |
| 主索引 | `knowledge/graph/index.tsv:400` | E174 行（severity=2，`manual-install`，`doc/E174.md`）；`E108` 行在 `:334` |
| doc 人读件 | `knowledge/doc/E174.md:11`、`knowledge/doc/E108.md:12` | 同一签名（E108 记 `install: No such file or directory|install.*not found`） |
| operations | `knowledge/operations/filesystem-analysis.md:271` | 场景行"`make install` 安装 man 页"的解决方案明确写着"**`make install DESTDIR=` 后手动复制**；或安装 GNU coreutils 的 `ginstall`" |
| drafts（手工扫，draft-review 不覆盖） | `knowledge/drafts/DRAFT-9848-qbe-device-e2e-runtime-evidence.md:88` | "无 `install(1)`（设备实测）→ `package()` 用 `copy()` 安装 `bin/qbe` + LICENSE + docs" |
| 同上 | `knowledge/drafts/DRAFT-E628-rtklib-handwritten-makefile-multi-app-adaptation.kv:85` | "`mkdir -p` + `cp -f`，不用 install(1)——设备 PATH 里没有它" |
| 同上 | `knowledge/drafts/DRAFT-ohos-makefile-explicit-toolchain-and-install-vars.kv:8`、`DRAFT-libfec-legacy-autotools-ohos-bootstrap.kv:13`、`DRAFT-8958-clthreads-makefile-stage-install-shadow.kv:17` | 同签名/同族的既有条目 |
| 归档先例 | `archives/*/*/notes.md` 内 `install: No such file`/`Error 127` 命中 20+ 包（qbe、rtklib、clthreads、libfec 等） | 已是反复复现的家族 |

**四条件逐条核**

1. 症状一致：**成立** —— 稳定错误签名 `make: install: No such file or directory` +
   `*** [GNUmakefile:18: install] Error 127`，触发条件"Makefile 的 install 规则调用宿主
   `install(1)`"与 E174 的 `affected_scope` 完全重合；探针未出现条目外的新行为偏差
   （`mkdir -p` 同规则内可用、只有 `install` 这一步 127，正是条目所述的"缺程序"而非"缺权限/缺路径"）。
2. 解法也已被该条目覆盖：**成立** —— 本包用的就是 E174 的 `manual-install`（不跑
   `make install`，在打包阶段以文件复制落位），并在 filesystem-analysis `:271` 里逐字
   写成了"`make install DESTDIR=` 后手动复制"；本包只是把"手动复制"落到 Conan
   `copy()` 上（同一 approach 的配方形态，不是条目没写的另一条路）。
3. 引用精确：**成立** —— 见上表"件:行号 + 复用的具体方案"，未使用"同族"式模糊引用。
4. 替代解法等效性：本包**没有**替换上游探测宏/编译语义；等效性论证=
   `install -m 0755 ries $(DESTDIR)$(BINDIR)` 与 `copy("ries", ..., bin/, keep_path=False)`
   的产物路径与文件内容一致（打包后 `bin/ries` 实测可执行，见 conan-verify 的 test_package
   9 条真机用例）；权限位方面 conan `copy()` 走 `copy2` 语义保留源文件模式，源二进制为
   `-rwxr-x---`，不依赖被 E046/E543 记载为"HMDFS 上不生效"的 chmod 调用。
   另一条已记录解法 `ginstall`（E108，`knowledge/doc/E108.md:20,26`）**未采用**，理由见
   `notes.md` A1 节（为省两行 copy 去拉 coreutils 依赖链，代价高于收益，且 CI 环境不预装）。

**结论：`B判定=hit(E174)`，不新建草稿、不建 Issue。**

> ⚠ 作用域标注（第 3 棒 2026-09-25 追加，未改写上行原文）：本行只判**候选 1 这一面**（缺 `install(1)` 已被 E174 覆盖）。**PR 级判定已因候选 3 改变**——本 PR 的知识位给"被测程序自报计时字段进逐字节比较"这条新机制，并按 `create` 需要一条知识库扩展 Issue（Issue 由主理创建后回填，见 notes.md 的 3+2 声明行与本文件末尾的唯一 PR 级判定句 `B判定=create(DRAFT-ries-2018.08.05-...)`）。

---

## 候选 2：上游无版本归档 + 官方源内容漂移 + PF7 源URL闸互斥

**症状**：上游 `mrob.com` 只发布滚动单文件 `src/ries.c.txt`（现网头部为
`This is the 2026 May 06 version`，462229B / sha256 `df335f02...`），无任何版本化归档
（4 个候选 URL 实测全 404，Wayback 双端不可达）；任务版本 `2018.08.05` 的钉版字节只能从
Debian pool 的 `.orig.tar.xz` 取（sha256 `725c004f...`，与 `.dsc` 的 `Checksums-Sha256` 一致，
且 `.dsc` quilt 补丁只动 `ries.1`，`ries.c` 为上游原样），而
`scripts/ohc/preflight.py` 的 `_PF7_DEBIAN_HOSTS` 把 `deb.debian.org` 列为硬拦对象。

**查重**：`knowledge/drafts/DRAFT-8543-conandata-comment-url-predl-rewrite.md:44` 已有
"用 Debian `.dsc` 的 Homepage + `Checksums-Sha256` 交叉验证**官方归档** sha256"的先例；
`knowledge/drafts/DRAFT-9200-lddtree-shell-tool-portability.md:147` 已记 PF7 硬闸口径；
`knowledge/graph/E271.kv:9-17` 覆盖"官方单文件资产"的配方形态（下载+sha256 校验+直接装到
`bin/`，不解包）。

**不升 B 的理由**：①本包最终**没有**采用任何新的技术解法绕开它——是否改用
`--no-preflight` 例外申报、还是回头改版本，是**待主理/平台裁决的政策判断**，
按手册第 78 行"不属于 B"口径（无已验证的可复用解法、结论未定案）不宜立项；
②候选 1 的实质技术障碍已被 E174 覆盖，本包不存在"新解题路径"；③若最终按
①落地，可复用的增量是"PF7 对'上游无归档'类包应给的例外通道"，属框架/规则改动，
应走规则件而非知识草稿。**如主理判定该走 ①并认为值得沉淀，可另立 B 草稿再报**
（取证已备齐：`notes.md` A3 节 + `~/tmp/uc2/z45-ries/logs/` + 本文件）。

---

## 其它检索过但不成立的候选（留痕）

- `init-build` 假红：根因是 `scripts/ohc/check_env.py:33` 的 `str(e)` 未绑定（框架代码缺陷），
  属"修一行 `except Exception as e`"的框架改动，单包知识价值为 0，且禁与本配方混提（W2）。
- `recipe-search ries` 语料 6173 条零命中：只说明无相似配方，不构成知识。
- 上游零测试（R51 清点）：如实披露即可，非机制（且"上游无测试不得写成通过率"已由
  `knowledge/graph/E253.kv:54-55`、`E265.kv:69`、`E319.kv:47` 作为 forbid 规则覆盖）。

---

## 附表：随 PR 的证据件与 sha256 对账（第 3 棒 2026-09-25 生成）

> 生成脚本 `~/tmp/uc2/z45-ries-b3/gen-ledger.py` 是设备本地一次性取数件（`~/tmp/` 属可丢弃区，**不随 PR**）；下表每一行都是它对**盘上真实字节**现算的 sha256，读者拿到随 PR 的件后可直接 `sha256sum` 复算。

搬运方式＝从设备可丢弃区 `~/tmp/` 原样 `cp` 进 `archives/r/ries/2018.08.05/reports/` 后 
`git add -f`（沿用本件 `reports/knowledge-candidate-ledger.md` 的 force-add 先例；`.gitignore:96` 把 `reports/` 整体排除）。
**日志正文一字未改**；下表每行「搬运前 sha256 = 搬运后 sha256」逐字对账通过，同 sha 的多件归并成一行。

| 随 PR 的件（`archives/r/ries/2018.08.05/` 下相对路径） | sha256 | 搬运前原件（设备可丢弃区） |
|---|---|---|
| `reports/assert9-det3/det3.sh` | `dd8be7f538da348b335fe82b2e4f01813e9b08a6b319fc921f375be1b73c4cd2` | `~/tmp/uc2/z45-ries/det3.sh` |
| `reports/assert9-det3/la.txt`、`reports/assert9-det3/lb.txt` | `c3bdffa4115d65ab539acd3f871a8762952b4b1631f7db5eadc2558175a50a79` | `~/tmp/uc2/z45-ries/fixcheck/` 同名件 |
| `reports/assert9-det3/load_a.txt` | `bc0e8ab38fa745d516aab675dc6567cbb8ea0bc249411900517a0c89ebccbf35` | `~/tmp/uc2/z45-ries/det3/load_a.txt` |
| `reports/assert9-det3/load_b.txt` | `0523fa0a5b50c9294135e0a2a42384f52a1de76725d85b412f6e4e66c9b1f966` | `~/tmp/uc2/z45-ries/det3/load_b.txt` |
| `reports/assert9-det3/md_full.txt` | `bf1b58c72c900de3dd7c67835234dda6fa80802b164b9609a2a9247f20ce2831` | `~/tmp/uc2/z45-ries/det3/md_full.txt` |
| `reports/assert9-det3/md_mask.txt` | `d561ff0a94fb34097f33d9bb42a3668c54cc4be832d96e11a57f8ded0e23ff99` | `~/tmp/uc2/z45-ries/det3/md_mask.txt` |
| `reports/assert9-det3/times.txt` | `9db6b4f0abfef6010b704f07172b49b79681c6cb6ebede00a18b006ce7a43a21` | `~/tmp/uc2/z45-ries/det3/times.txt` |
| `reports/assert9-fixcheck/harness-recheck.log` | `8e6b25035f79f988102cd244096d2a8bccd41044badab191dbdc5fd6504a4eeb` | `~/tmp/uc2/z45-ries-b3/harness-recheck.log` |
| `reports/assert9-fixcheck/harness-recheck.sh` | `1fc8760889fdb797ee3a75c578e26bd6f69b94edfc3f5222df1edccc6a9d4617` | `~/tmp/uc2/z45-ries-b3/harness-recheck.sh` |
| `reports/assert9-fixcheck/new1.log`、`reports/assert9-fixcheck/new2.log`、`reports/assert9-fixcheck/new3.log`、`reports/assert9-fixcheck/new4.log`、`reports/assert9-fixcheck/new5.log`、`reports/assert9-fixcheck/new6.log` | `5c9c1655981577e96e8e21d8b64922b013a8cacd607ec4b083305a8d8197940b` | `~/tmp/uc2/z45-ries/fixcheck/` 同名件 |
| `reports/assert9-fixcheck/old1.log`、`reports/assert9-fixcheck/old2.log`、`reports/assert9-fixcheck/old3.log`、`reports/assert9-fixcheck/old5.log`、`reports/assert9-fixcheck/old6.log` | `d103f1193fb54661b1884eabaa9e5e6969488d1a07ea063fe275756fafae9053` | `~/tmp/uc2/z45-ries/fixcheck/` 同名件 |
| `reports/assert9-fixcheck/old4.log` | `a1482ac7a4185f3d3012bcdc2e61c5a3a6200ef3184fd852fc7137ab551ea74b` | `~/tmp/uc2/z45-ries/fixcheck/old4.log` |

- `reports/w3-local-ci.log` = `54cffa428df5b7847f9d1300cffb7acfb81b6ec32df116dab784cf9e0937bf87`（末轮 9/9 原件，第 224 行 `RIES_TEST_SUMMARY total=9 passed=9 failed=0`）；与本地凭据件 `.ci-result.json` 的 `log_sha256` **全串一致**（`exit_code=0`、`step=W3_local_ci`、`timestamp=2026-09-25T19:05:37.725094`），该凭据件按 `.gitignore:238` 不随 PR。
- 18:50 那一轮的 W3 日志**无法随 PR 提供**：框架按同一路径原地覆写，现存内容即末轮 9/9。翻面那一轮由同臂复跑件 `assert9-fixcheck/old4.log` 承担（见 notes.md 断言 9 修订记录）。
- 改后的 `test_package/test.sh` = `8c6f5d0df0563537744a65805a872d2b3409b89286e963186155d8bdeea3ba6b`；`reports/assert9-fixcheck/harness-recheck.log` 的 A 节自证它跑出的 4 轮 9/9。

- 对账结果：**22 件全部逐字一致，0 异常**。

---

## 候选 3（第 3 棒补记，2026-09-25）：被测程序自报的计时字段进了消费者逐字节断言 ⇒ 随机假失败

**机制一句话**：确定性求解器的正常输出里带一枚**不可抑制的墙钟字段**——ries 在 `print_end()`
里 `tsec = gettime()`（`ries.c:7511`）后 `printf("  Time: %.3f\n", tsec)`（`ries.c:7540`，
2018.08.05 钉版行号），任何 CLI 选项都关不掉它；把它纳入"两次重跑逐字节一致"的比较面，
断言就在原理上不可复现（机器越忙越容易翻面）。修法＝**字段级掩码 + 字段级正对照**。
草稿件：`knowledge/drafts/DRAFT-ries-2018.08.05-self-reported-timing-field-in-byte-comparison.{kv,md}`。

### 四范围检索式与行号级读数（第 3 棒在 B 机 worktree 与 Windows 侧池子各自实跑）

取数脚本 `~/tmp/uc2/z45-ries-b3/kbsearch.sh` 与其完整输出
`~/tmp/uc2/z45-ries-b3/toollogs/kbsearch.log` 属设备可丢弃区、**不随 PR**（只读取证，不改任何件）；下表已把关键读数逐条照录，读者可在自己的 worktree 里用同样的三档词集复算。
词集分三档：`A = stopwatch|elapsed time|wall[._ ]clock|clock_gettime|non[._-]determinis`、
`B = 逐字节|秒表|计时字段|墙钟|随机失败|flaky`、`C = "Time:" + 空格`。

| 范围 | 检索式 | 实测命中 | 代表件:行号与所在层次 |
|---|---|---|---|
| ① `knowledge/graph` + `doc` + `operations` | A | **25** | `E152.kv:4,12`（`CLOCK_REALTIME`/`CLOCK_MONOTONIC` 宏未定义）、`E270.kv:8,12,17,30`（`clock_gettime(CLOCK_SGI_CYCLE)` 运行期 `EINVAL`）⇒ 层次＝**时钟源/宏在 OHOS 可不可用** |
| ① 同上 | B | **23** | 最近邻 `E057.kv:8,13,16,19,23`（regrtest 按 `os.cpu_count()` 开 worker、load avg 高 ⇒ **真**不确定，`rec_approach: env-var-override`）；`E528.kv:35`、`E330.kv:39` 的 flaky 只出现在 `forbid_*_reason` 里；`E488.kv:40,70` 的"逐字节"是 HMDFS 上重写 `.so` 的手法 ⇒ 无一涉及比较面 |
| ① 同上 | C | **2** | `E537.kv:45`、`E537.md:36` 的散文 `at link time: (1) stamp an` ⇒ 字面假阳性 |
| ② `knowledge/drafts`（手工 grep——`draft-review` 只取 `knowledge/graph/index.tsv`，不扫本目录） | A | **19** | `DRAFT-10686-skypat-perf-events-runtime-capability-probe.kv:42` 与 `.md:64,154`、`E558-draft-7899.kv:78`/`.md:43,233`、`E544-draft-A7F3.kv:16,27`/`.md:25`、`E430-draft-7707.kv:42`/`.md:13,32` ⇒ 全是取时/符号可用性，层次＝**被测程序怎么取时间** |
| ② 同上 | B | **171**（量大，逐件核对代表性） | `DRAFT-13503-libamrnb-amr-codec-test-properties.kv:41`（`Flaky/false test failures` 在 forbid 理由里）、`DRAFT-5851-lomiri-schemas-*.kv:54`/`.md:30`（"逐字节等价"＝**产物拷贝**等价）、`DRAFT-8543-refresh-patch-rename-conandata-desync.kv:19,56`（补丁内容逐字节相同）、`DRAFT-9200-lddtree-shell-tool-portability.kv:57`（上游 tests 逐字节未改＝不许擅改上游测试件）、`DRAFT-9645-polyseed-*.kv:27`/`.md:15`（UTF-8 逐字节拷贝）、`DRAFT-8425-libusbsio-*.kv:9,14`/`.md:19,30`（**产物**字节级对照判等价源）⇒ 层次各异 |
| ② 同上（第 3 棒再实读到行的 4 件，语义最近的一批） | B 组 | 4 件逐件读到行 | `DRAFT-9995-f3d-vtk-gles-egl-upstream-tests.kv:39,55`（OpenGL 常量名 `GL_TIME_ELAPSED`，与"输出里的耗时"无关）、`DRAFT-8959-kqwait-1.0.3-kqueue-to-inotify-faithful-rewrite.kv:33` 与同名 `.md:52,60`（**移植义务**要求 CLI/输出/退出码逐字节一致，是"别改输出"而非"别比时钟"）、`DRAFT-E577-buffer-sysv-ipc-posix.kv:47`（两份**产物** `cmp` 逐字节一致）、`DRAFT-E616-upstream-auto-tarball-vs-release-src-asset-submodules.md:92,95`（tarball 与目标树逐字节 diff）⇒ 四层都不是"消费者比较面含自报时钟" |
| ② 组合探针（同时含取时与逐字节语义） | `grep -rliE "clock_gettime|stopwatch|elapsed time"` | 4 件（10686 / E558 / E544 / E430） | 无一条写"消费者比较面里的自报计时字段" |
| ③ 仓内 prescan/规则件 `scripts/`、`ci/`、`docs/` | A + `逐字节比较` + `byte-identical` | **0** | 只有 python 自身计时变量（`budget.py`/`driver.py`/`submission.py`），无规则 |
| ④ Windows 侧池 `经验文档/B草稿库/`（23 份 `.kv`） | A | **0** | — |
| ④ 同上 | B | **2** | `DRAFT-PKG-VER-hishell-swallows-sigalrm.kv:44` 与同名 `.md:64`——那里的"父进程墙钟"是 **M15 的第三条修法**，不是被掩字段 |
| ④ 同上 | `逐字节|byte-identical|byte for byte|cmp -s` | **0** | 池内无任何逐字节比较类条目 |

**与 W4 判决件的差异（如实留痕）**：审计 `items.item4` 记的是"四范围对机制特征词**零命中**"，
用的是任务书下发的较窄词集。第 3 棒把词集放宽后，范围 ①② 出现上表的**字面命中**，
故本台账不沿用"零命中"表述；逐条核对层次后**结论不变**（机制级命中数＝0，判 create）。

### 与最近邻的方向对照（M15）与层次差（三条都对齐到行号）

- 池内 **M15** = `经验文档/B草稿库/DRAFT-PKG-VER-hishell-swallows-sigalrm.kv`
  的 `:7` title、`:10` error_signature、`:16` root_cause、`:41` rec_description
  （池索引行 `README.md:31`）。**方向相反**：M15 是上游用信号实现超时、被 hishell 吞掉 ⇒
  **该失败的没失败**（假通过 + 少报超时）；本条是被测程序自报耗时进逐字节比较 ⇒
  **该稳定的不稳定**（假失败）。症状、根因、修法三者皆不同。
- 正式条目里的最近邻是 `knowledge/graph/E057.kv`（`:8` 签名含 `flaky.*re-run`、
  `:16` root_cause 是 `os.cpu_count()` 开满 worker、`:23` `rec_approach: env-var-override`）：
  它处理**真实不确定源**（并发与负载污染测试），本条处理**把不可比的东西放进比较面**；
  本包实测限并发/换 env 都无效——加 6 枚 spinner 后掩码前 `cmp` rc=1、掩码后 rc=0
  （`reports/assert9-det3/load_a.txt` 与 `load_b.txt` 同 sha 家族件 `la.txt`/`lb.txt`）。
- 既有两族口径（"同一 test.sh 原生全绿而 conan 下差 1 条 ⇒ 先查 CWD / 两臂输入字节 /
  env 三臂"、"L1e 把参考输出相对写到 cwd 被负照轮覆写"）讲 **harness 落点与环境**；
  本条差异来源在**被测程序自身的 printf**，双臂同臂、同 cwd、同 env 也必然翻面。
  本包 notes.md 的排除项 2、3 正是先按那两族否证环境说，才落到时钟说 ⇒ 互补的排查顺序，
  不是同一条知识。

### 四条件复核与判定

1. 症状一致：**不成立**（E057 症状是真并发污染，M15 是假通过）；
2. 解法已被该条目覆盖：**不成立**（限并发/换 shell 都掩不掉 `Time:` 字段，见上）；
3. 引用精确：上表全部到行号，且 `draft-review` 实跑 TOP3 相似度最高仅
   `E453 score=0.08`（`sig=0.14 kw=0.0 cat=0.0`），无高相似条目；
4. 等效性：**无既有条目可等效替代** ⇒ 新知。

工具实跑（只读，RC 全 0）：`draft-review` 预审建议 **create**、质量预检
`signature=✅ root_cause=✅ rec=✅`；`ci/scripts/knowledge_check.sh` `KC_RESULT=pass`
`KC_ERRORS=0`；`ci/scripts/junk_check.sh` RC=0。日志
`~/tmp/uc2/z45-ries-b3/toollogs/{draft-review,knowledge_check,junk_check}.log` 属设备可丢弃区、不随 PR，此处照录关键读数。

候选 1 的 hit 结论对"缺 `install(1)`"那一面依然成立，只是**不再占用本 PR 的知识位**
（按文件名引用；PR 级口径见 notes.md 的 `## 路径 B 判定` 节）。

**B判定=create(DRAFT-ries-2018.08.05-self-reported-timing-field-in-byte-comparison)**

---

## 同源复扫留痕（第 3 棒，2026-09-25 改后）

扫描面＝本包**两级同名文件全含**：`archives/r/ries/commands.json`（软件级，本包软件级只有这一件）、
`2018.08.05/manifest.yaml`（版本级）、`2018.08.05/notes.md`、`2018.08.05/test_package/MANIFEST.yml`、
`2018.08.05/reports/*`（含本次新带的 `assert9-*` 与 `w3-local-ci.log`）、
`knowledge/drafts/DRAFT-ries-2018.08.05-*.{kv,md}`。

1. **断言数三处同源**：`test_package/test.sh` 的计数器实测 `total=9 passed=9 failed=0`
   ＝ `reports/w3-local-ci.log:224` ＝ `reports/assert9-fixcheck/new1-6.log`（6 轮同臂）
   ＝ notes.md 五维账本"9 / 0 / 0" ＝ `test_package/MANIFEST.yml:30,31`
   的 `assertion_count: 0` / `adapted_assertion_count: 9`；
   `MANIFEST.yml:26` 的用例描述已是"除上游自报的 `Time` 秒表字段外逐字节一致"，与改后的字段级口径一致。
2. **分母口径未被改动**：上游三个维度仍为 0（`make -n check/test` rc=2 的目标全集读数见 notes R51 节），
   `grep -c "assert(" ries.c` 复算＝0 ⇒ 消费者 9 条是本包新增，不冒充上游通过率。
   ⚠ `reports/w3-local-ci.log` 尾部的 `Total: 1 / Success: 1 / Pass rate: 100.0% (1/1)`
   是框架**按包**统计（1 个包的一次构建），**不是用例通过率**；用例通过率只按第 1 条的 9 口径读。
3. **F6 类过头表述**已改精确：notes 的源码计数句现在写成"作为可执行调用 0 命中"，
   并把三处字面命中（`:106` 注释公式、`:105`/`:2479`/`:2575` 注释散文）与调用式 ERE 的
   唯一命中行（`ries.c:106`）分开列。
4. **conandata/conanfile 一个字节未动**：第 3 棒改动过的文件全集只有
   `test_package/test.sh`、`notes.md`、`reports/**`（新增证据件）与根目录 `knowledge/drafts/**`；
   `git diff 33c7831826..HEAD --name-only` 里 `conandata.yml` 与 `conanfile.py` 均不出现 ⇒
   recipe revision 不变，已到的 W3/verify/finish 证据继续有效（时间线见 `notes.md` 尾注与
   `.ci-result.json` 的 `log_sha256` 对账行）。
5. **未取新源、未绕闸**：候选 2（PF7 取源）保持第 1 棒结论与主理裁决，本轮未改任何 source URL，
   未改 `ci/`、`scripts/` 任何脚本，未动 git 配置。
