# snpomatic 1.0 适配笔记

## 编译环境
- 构建系统: makefile（上游裸 Makefile，15 个文件，无 configure、无 autotools）
- 编译日期: 2026-09-25
- 编译器: clang/clang++ 15.0.4（HarmonyOS PC aarch64，profile `ci/conan/profiles/ohos-aarch64`，`compiler.cppstd=17`）
- 状态: built（conan create 通过，未 upload）
- CONAN_HOME: `~/tmp/ch/home-snpomatic`；worktree `~/qzy/主理-32-snpomatic-1.0`，分支 `feat/snpomatic-1.0`

## 派活前台账三条复验（否证式，逐条给读数）

候选描述里的三条前提全部实测过，**其中一条为假、一条口径错位、一条成立**：

| # | 台账说法 | 实测 | 结论 |
|---|----------|------|------|
| ① | 文档链需要 asciidoctor 与 antiword，默认目标会拖出生成步骤 | 解包归档 `Makefile` 全文 35 行：目标只有 `findknownsnps`(13) / `reassemble`(16) / `variety`(19) / `mapcontigs`(22) / `ungap`(25) / `.cpp.o`(28) / `clean`(31)；**没有 `all`、没有 `install`、没有任何文档/man 规则**；`grep -rni "asciidoctor\|antiword" 解包树` = **0 命中** | **假前提（口径错位）**：asciidoctor/antiword 是 Debian `debian/rules` 的 `override_dh_installman` / `override_dh_installdocs`（见 `dsc.tar.xz` 9620 B（解包得完整 debian/）：`debian/rules`:22 antiword、:39 asciidoctor、`debian/control`:7 asciidoctor、:8 antiword ⇒ rules 第 22/39、control 第 7-8 行 B-D；盘上另一 `snpomatic_1.0.debian.tar.xz` 仅 300 B、非 Debian 归档不可复算，不引它），与本 tarball 无关 ⇒ 无需关文档目标，也**不需要任何"删文档目标"的平台宏补丁** |
| ② | 零编译依赖 | `Makefile:4` `LIBS=-lm`；`#include` 全集 = STL（iostream/string/vector/map/algorithm/fstream）+ POSIX（stdio/stdlib/string/unistd/getopt/time/sys-types/sys-stat），无 zlib/无第三方头 | **成立**：零第三方编译依赖（libc/libm 由工具链提供），`requires()` 为空 |
| ③ | 上游 GitHub tag 归档 == Debian .orig | tag 名实测 `refs/tags/v1.0`（`1.0` 不存在，404）；两端均 **66546 B**，sha256 同为 `b90123226e24edfa5c2ca296f9414b5aa005d3da77ad80b5c576adddbb38a094`，`cmp` 0 差异，解包顶层目录同为 `snpomatic-1.0/` | **成立** ⇒ `sources.url` 写官方 tag 归档，`sha256` 一字未动（PF7 归零） |

②之外另发现一条**台账没写**的真问题（这才是本包唯一的技术障碍）：
`ungap` 目标在 tag v1.0 源码不自洽 —— `src/ungap.cpp:261` 用 4 个实参调用
`ca.align_solexa_paired ( fastq_file , pair_length , fragment_length , variance )`，
而声明 `src/snpomatic.h:179` 是 5 参且**无默认实参**：
`void align_solexa_paired ( string filename , string filename2 , uint read_length_1 , uint fragment_length , uint range )`。
真机首条错误：`src/ungap.cpp:261:81: error: too few arguments to function call, expected 5, have 4`。
同一棵树里正确用法见 `src/findknownsnps.cpp:312-313`（5 参调用）⇒ 与平台/编译器无关的**上游笔误**；
上游 master 的 `src/ungap.cpp:261` 至今仍是同一行（实测 raw 抓取，9932 B）。
Debian 侧用 `debian/patches/fix_ungap` 把它补成 `align_solexa_paired ( genome_file, fastq_file , ... )`。

**处置**：不吞错误（`make` 的 `Error 1` 原样留在证据里）、不改上游源码、不打补丁
（补什么语义要猜，越界），把构建目标显式写成上游四个可编译程序，并把上面的
可复算证据写进本节 + `ungap` 的 `not_built` 记进版本级 manifest。

## 编译步骤

真实编译（同一命令形态即配方 `build()` 的形态）：

```bash
export CONAN_HOME=$HOME/tmp/ch/home-snpomatic
make CXX="/data/service/hnp/bin/clang++" -j1 findknownsnps reassemble variety mapcontigs
```

- 上游 `Makefile:2` 写死 `CXX=g++`（B 机没有 g++），用 **make 命令行变量**覆盖
  （命令行赋值优先于 Makefile 内赋值），因此不改一行上游代码；
  `CXXFLAGS=-g -O3` 与链接行 `$(CXX) $(CXXFLAGS) $(LIBS) $^ -o $@` 保持上游原样。
- 配方侧 `CXX` 从 `tools.build:compiler_executables` 字典取 `cpp` 键（R33；
  本仓 profile 键名是 `cpp` 不是 `cxx`）。
- 上游**没有 install 目标**，也没有 `install(1)`（OHOS 无 coreutils install）⇒
  `package()` 手工 `copy()` 四个产物到 `bin/`，另把 `gpl-3.0.txt` 收进 `licenses/`、
  `doc/Manual.doc` 收进 `doc/snpomatic/`。
- 零补丁：`export_conandata_patches()` / `apply_conandata_patches()` 都保留为
  字面判据，实参是 `patches: []`（空操作），**本包无任何补丁**。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 裸 `make` 只产出 `findknownsnps` 一个程序 | 上游 Makefile **无 all 目标**，默认目标＝首条规则（Makefile:13） | 配方显式枚举 4 个构建目标（不靠 `make` 默认、不给上游补 `all:`） |
| 2 | `ungap` 编译失败 `too few arguments ... expected 5, have 4` | 上游 tag v1.0 源码笔误（ungap.cpp:261 vs snpomatic.h:179），master 至今未修 | 不构建该目标 + 完整披露；不打补丁、不改源码、不 `\|\| true` 吞错 |
| 3 | `make` 里 `CXX=g++` 在设备上没有对应编译器 | 上游 Makefile 写死 CXX，且 B 机无 g++/c++ | make 命令行覆盖 `CXX=<profile cpp>`（配方从 Conan conf 取值，R33） |
| 4 | `init-build` 在本机不可用 | `scripts/ohc/check_env.py:33` 的 `str(e)` 未绑定（探测 `automake` 失败后抛 `NameError`，把该框架自检的"非阻塞警告"变成整命令崩溃） | 按 SKILL R13「脚本失败＝手动模式入口」走手写配方 + `conan-verify`/`finish` 真门禁；**不改 scripts/**，症状已记入本笔记与交回报告 |

## 源码修改

无。零补丁、零平台宏（R8/PF5：`patches/` 目录本包不存在，`__OHOS__` 0 命中）。

## 依赖版本

零第三方编译依赖（`LIBS=-lm`）。W0 判决见「验证结果」节 preflight 行。

## 上游测试账（R51/rule4 六形取证）

上游自动化测试 **0** 项，六形取证与可复算命令见 `test_package/MANIFEST.yml` 顶部注释
（tar 清单 / Makefile 目标 / CI 文件 / 语料 / 源码自测 / 自带测试脚本，逐形 0 命中）。
Debian 的 `debian/tests/test-example`（依赖 wgsim+samtools）属**下游打包件**，
不在 upstream tag 内 ⇒ 不计上游分母，但其"喂读段再断言输出件"的思路被本棒
test_package 用自造冻结语料复现，且不引入 samtools 依赖。

适配后断言：**18** 条，全部在 `test_package/test.sh`，末行有
`[ "$n" = "18" ]` 防漂移自检；期望输出**取自 B 机真跑产物**（下方原文），
不是失败残件 —— 已核 `grep -rl 'failed to run command\|No such file or directory' test_package/` = 0 命中。

同源 5 处（数字必须一致 = 18）：
`test_package/MANIFEST.yml: assertion_count`、`test_package/conanfile.py` 文档串下限、
`test_package/test.sh` 自检、版本级 `manifest.yaml: assertion_count`、本笔记。

## 验证结果

（本节的门禁判决行、字节与 mtime 在跑完后追加于「门禁台账」一节，逐条给出处。）

真机功能读数（2026-09-25，findknownsnps 1.0，`ref.fasta` 216 bp + 5 条读段，sha256 前缀 b90123226e24）：

```
Reading all chromosomes from ref.fasta ... read 1 chromosomes.
Indexing 1 chromosomes ... sorting ... done.
Reading solexa data from reads.fasta ... scanned 5 solexa reads, 2 (40.00%) matched , 2 total matches.
```

行为观测（**不计入断言数**，单列的平台/上游观测）：
- 上游四个程序都没有 `--version`；`--version`/`--help` 都落到
  `unrecognized option: ...` + 用法打印，且**退出码恒 0**（含"缺 genome"错误路径）。
  ⇒ 本仓 L2 smoke 以 `--version` rc 判绿会把这条**错误路径**当成功；
  故 test.sh 一律押输出内容，不押退出码。
- 首跑 ad-hoc 构建产物（未经 conan 签名链）在本机可直接 exec，未见 126/EPERM。

## 交付物

| 文件 | 说明 |
|------|------|
| `1.0/conanfile.py` | 配方（application，零依赖，零补丁） |
| `1.0/conandata.yml` | 官方 tag 归档 URL + sha256（与 .orig 同值） |
| `1.0/test_package/{conanfile.py,test.sh,MANIFEST.yml}` | 18 条断言 |
| `1.0/manifest.yaml` `1.0/notes.md` | 元数据 |
| `README.md` `manifest.yaml` `commands.json` | 软件级三件套（R38/L0k） |
| 包内 `bin/` | findknownsnps / reassemble / variety / mapcontigs |

## 路径 B 判定（一 PR 一知识）

- **适配路径**：A（裸 Makefile 直接编译；**补丁数 0**（`patches_applied: []`）、零平台宏）
- **使用知识库**：是 —— 命中在池条目 `knowledge/drafts/DRAFT-commander-1.4.0-makefile-recipe-build-package-traps.kv`
- **知识库扩展**：无新增条目（本包触到的机制全部被在池条目覆盖，见下表四条件对齐）
- **关联 Issue**：无需新建（路径 B=hit，机制已被 `knowledge/drafts/DRAFT-commander-1.4.0-makefile-recipe-build-package-traps.kv` 与 `knowledge/graph/E174.kv` 覆盖）

| 本包机制 | 在池条目 | 四条件对齐（同机制/同根因/同处置面/同作用域） | 判定 |
|---|---|---|---|
| 裸 Makefile 无 configure/无 install 目标，`basic_layout` 下 `self.run()` cwd 落在 build 目录、编译器必须从 `tools.build:compiler_executables` **字典**（本仓键名 `cpp`）取，模板 `:c` 单项写法在 Conan 2.29.1 抛 conf 异常 | `knowledge/drafts/DRAFT-commander-1.4.0-makefile-recipe-build-package-traps.kv` 第 12-15、24-28、30-31 行 | 同机制（makefile 型配方 build/package/test 三面）／同根因（basic_layout cwd ＋ conf 字典型）／同处置面（chdir source_folder ＋ `check_type=dict` 取 `cpp` ＋ 手工 copy）／同作用域（该行 30-31 明写"所有无 configure/无 install 的裸 Makefile 型 C/C++ 配方"） | **hit** |
| 上游无 install 目标 ⇒ 产物手工安装 | `knowledge/graph/E174.kv` 第 13-17、22-26 行（root_cause 明写"OpenHarmony 缺少 GNU coreutils 的 install 命令 … 需要手动 cp"，`affected_scope` 为"使用 Makefile install 目标的项目"） | 同处置面（cp 替代 install）一致；**根因不齐**（本包上游 Makefile 全文 35 行、0 个 install 目标，失败链从未触发 install 缺失）、**作用域部分对齐**（E174 作用域为"使用 Makefile install 目标的项目"，本包是其弱化情形） | **同处置面命中（作用域部分对齐，按 E174 处置，不另立条目）**；四条件齐的主锚点是上一行的 commander makefile-recipe 草稿 |
| 上游 tag 归档与 Debian .orig 逐字节相同 ⇒ 取官方 URL、哈希不动 | 已在多处 notes/条目中作为常规做法（本窗 rubiks/mpdas/inputlirc 四次实证同族） | 非"OHOS 平台机制"，属取源纪律，已由 PF7/R39 门禁本身覆盖 | 不升 B |
| `ungap` 目标源码不自洽（4 实参调 5 参）而默认目标不受影响 ⇒ 只构建可编译子集并披露 | **家族已有零散条目、无同机制条目**：四范围检索（`knowledge/graph/*.kv`、`index.tsv`、`knowledge/drafts/*.kv`、`archives/**/notes.md`）按机制特征词 `too few arguments`、`upstream defect`、`构建子集`、`非默认目标` 未发现在池同机制条目；但「上游缺陷 ≠ 平台缺陷」处置面已有 ≥5 条同族零散条目（`DRAFT-bison-pure-parser-yylex-signature.kv`、`DRAFT-gamelib-1.9.9-dual-backend-single-header-game-lib.md`、`DRAFT-arb-2.9.0-flint3-merge-compat.kv`、`DRAFT-autoloader-autoload-not-imported.kv`、`DRAFT-gated-sublib-dual-archive-closure.md`）⇒ 属**家族命中**而非孤立事实 | 四条件中「同机制/同根因」不齐（家族条目均为别的上游缺陷形态），仅处置面同族 | **降档：本 PR 不占第二知识位、不建 Issue**。按 `AGENTS §9` 将机制投入 `经验文档/B草稿库/` 通用池（建议名 `DRAFT-snpomatic-1.0-upstream-nondefault-target-source-defect`：非默认目标源码不自洽 ⇒ 显式枚许可编译目标子集 + 保留 `make` 的 `Error 1` 不吞错 + `not_built` 三处台账 + 上游 master 复测）；本包只有 1 个知识位，已让给覆盖面更大的 makefile-recipe 家族 hit。**该缺陷仍按上文处置面完整处置（不构建、不吞错、三处披露），不作"无需处置"降级** |

## 注意事项

- `conan create` 之后 `conandata.yml` 可能被预下载改写成镜像数组 ⇒ 建 PR 前要从 HEAD 还原并核禁词（本轮复跑实测：还原前 `preflight.py` 会报 PF7 镜像前缀，还原后 PF7 归零）。
- 源码缓存链路（2026-10-03 收尾轮实测）：E017 注入的 `ghfast.top` 镜像 `curl -m 20` 超时不可达 ⇒ G2 改走 `core.sources:download_cache`（`~/tmp/ch/dlcache`）按 conandata 声明的 sha256 **本地命中**（`s/<sha256>` 66546 B，与官方 tarball 逐字节一致），无网可复现；W3 走 predl `file://` 本地缓存同理。过程中清掉过一条 11:36 由 W3 写入的 `<sha256>.json` 备份边车（它只登记 `file://` 来源，会让 conan 判"来源不符"强制重下），复验成功后该边车已由 conan 自动重建（现登记 ghfast URL）——**内容文件与 sha256 全程未改**。
- 上游程序对错误路径 `exit 0` ⇒ 任何"非 0 即通过"的测试口径对本包全无效（已在 test.sh 里避开）。
- 交付的是上游 5 个目标里的 4 个；若主窗决定采纳 Debian `fix_ungap` 以补齐第 5 个，
  那是**改上游源码**的独立决策，需另立补丁件与语义论证，不在本棒范围。
## 门禁台账（本机真跑，判决行原文 + 出处 + 字节/mtime）

| 门禁 | 判决行原文 | 出处 | 字节 / mtime |
|---|---|---|---|
| W0 依赖预检 | 「[OK] 预检通过（无依赖需要检查）」（上一行 「[INFO] 未找到依赖声明……」＝本包零 requires 的正常形态） | bash ci/scripts/preflight_check.sh snpomatic/1.0 | 开工 2026-09-25 07:31 与收尾轮 2026-10-03 复跑，两轮均 rc=0 |
| recipe-search | 开工时 archives/s 下无 snpomatic 目录（git ls-files archives/s/snpomatic = 0 行）⇒ 非重复交付；收尾轮复跑 top1 = 本包自身 snpomatic/1.0 score=0.5+补丁（配方已并入检索语料，非他人同名件） | scripts/ohc-run.py recipe-search snpomatic | 收尾轮 2026-10-03 复跑 rc=0 |
| conan-verify G0-G4 + L2/L4/L5 | 「**Verdict**: PASS」＋ G0/G1/G2/G3/G4 全 PASS ＋「✅ 配方验证通过: snpomatic 1.0」，VERIFY_RC=0（三一致：文字 PASS ＋ Verdict 行 ＋ rc） | archives/s/snpomatic/1.0/reports/conan-verify-report.md | 1466 B / 49 行（实测 4 轮：2026-09-25 一轮、2026-10-03 三轮，字节恒定）；mtime 每轮覆盖，以当轮文件为准 |
| G2 内 test_package | 「ALL PASS (18 assertions)」，ok 1..18 逐条在档；**不变量可复算**：`grep -c "  ok "` = 18、`grep -n "ALL PASS" reports/conan-create.log` 即末行、`grep -n "ok 1 -"` 与 `grep -n "ok 18 -"` 定位首末条 | conan create --test 输出 → archives/s/snpomatic/1.0/reports/conan-create.log | 收尾轮实测 **113 行 / 4885 B**（ok1@94、ok18@111、ALL PASS@112；2026-10-03 三轮复跑同读数）。⚠该件被每轮复跑覆写且随 conandata 状态变（镜像数组轮实测 219 行 / 14817 B）；`reports/` 属 .gitignore:96 本机件、不随 PR 走 ⇒ **核验口径钉不变量，字节只作当轮留痕** |
| W3 = finish step5 | 「✅   ✅ W3 本地 CI 模拟通过」；`grep -c "RESULT="` = 8 且 `grep -c "RESULT=pass"` = 8（2026-10-03 三轮复跑 8/8 恒定；[step] 行 47–48 条随轮浮动）；**L2 行自证含 failed**：`grep -n "L2_RESULT" reports/w3-local-ci.log` → `L2_RESULT=pass: findknownsnps --version OK, mapcontigs --version OK, reassemble --version OK, variety failed` —— 四程序无 `--version`、错误路径恒 exit 0 ⇒ `--version` 口径对本包天然失真，**该 pass 不作可执行证据；可执行证据＝G2 test_package 18 条真跑断言** | archives/s/snpomatic/1.0/reports/w3-local-ci.log | **字节/行号随复跑漂移（实测 18371→18260→17937→17815 B；L2 行 319→314）⇒ 不钉字节，只钉判决行与 8/8 计数**；本件属 .gitignore:96 |
| .ci-result.json | 字段 8 枚齐（software/version/step/timestamp/exit_code=0/integrity_hash/log_sha256/archive_dir）；**HEAD 绑定核验（建 PR 前必跑，两条命令）**：① `git -C <worktree> log -1 --format=%cI` 的时刻 **早于** 本件 `timestamp`；② 复算 `sha256("<timestamp>:snpomatic:1.0:0")[:16]` == `integrity_hash`、`sha256(reports/w3-local-ci.log)` == `log_sha256`（python3 hashlib） | archives/s/snpomatic/1.0/.ci-result.json（.gitignore:238 本机件） | 值随每轮 finish 更新 ⇒ **不钉值、钉公式**；收尾轮两组实测读数写进登记表备注与终报 |
| graph validate | 「✅   ✅ graph validate 通过」（同屏 E219/E253/E305 的 root_cause 或 rec_approach 为空，属全仓存量告警，与本包无关） | finish step7 / scripts/ohc-run.py graph validate | 收尾轮 finish 日志（本轮 finish-2.log 起各轮一致） |
| PF1-PF9 | conandata 还原为官方 URL 后复跑：**仅 PF9 照红**（软件级 README/commands/manifest 落在「包」层 vs PF9 要求「包/版本」层，两闸互斥，见未过项 4），**PF7 归零**（官方 tag URL，禁词 0 命中） | python3 scripts/ohc/preflight.py . origin/main HEAD | 收尾轮 2026-10-03 读数（还原前实测 PF7 会因镜像数组误红 ⇒ 还原是硬前置） |

### 未过项（照红，不凑绿）

1. **step5b 知识引用 unreferenced=3**：finish 报「⚠️ manifest.yaml: knowledge_count=3 unreferenced=3」「存在知识遗漏: pending=0 failed=0 unreferenced=3」。版本级 manifest 的 knowledge_gained 三条是本包自述、不指向往池 E 编号，故被判未引用；全仓存量比例极高（手册口径：披露即可）。判决行：「  ⚠️    失败步骤: step5b, step8」。
2. **step8 gen_summary 框架异常**：「⚠️   gen_summary 失败: 「str」 object has no attribute 「append」」（原文用反引号，此处为避免 shell 展开改书名号）。属 SUMMARY.md 生成器缺陷，非本包问题，不改 scripts/。
3. **L2/L4/L5 = 跳过（无 cache 路径）**：报告里三行都是「⏭️ 跳过（无 cache 路径）」却记 ✅ PASS ⇒ 属框架预期，**不得当可执行证据**；本包真正的可执行证据是 G2 内 test_package 的 18 条真跑断言。另上游四程序都没有 --version 且错误路径恒 exit 0，故 L2 口径对本包天然失真，已在「注意事项」披露。
4. **PF9 × 软件级三件套互斥**：PF9 要求所有 archives 变更落在「包/版本」层，而 R38/PF8 要求软件级 README.md/manifest.yaml/commands.json 落在「包」层 ⇒ 两闸互斥。origin/main 已有数千枚软件级 commands.json 同形合入 ⇒ 判框架缺陷，**不删件凑绿**。
5. **submit 就绪预检 3 项未创建**：test-report.md、packaging/、.staging-verified（finish step10 三行 ❌）。reports/ 在 .gitignore:96 内、不随 PR 走；本轮按流水线口径建 PR（不经 ohc submit 的就绪预检），三项按原样披露、**不凑绿**。
6. **ungap 目标未交付**：上游缺陷，见上文「遇到的问题与解决方案」表第 2 行与版本级 manifest 的 not_built 字段。
7. **init-build 不可用（框架）**：scripts/ohc/check_env.py:33 引用未绑定变量 e，探测 automake 失败后整命令抛 NameError ⇒ 按 SKILL R13「脚本失败＝手动模式入口」走手写配方 ＋ conan-verify/finish 真门禁，未改 scripts/ 一行。

> 收尾说明：finish 每轮会把文件末尾的收尾块删除后按当轮时间重新追加（本节台账不随其移动）；下一块的时间与收尾轮 `.ci-result.json` 同轮。
---

**编译结束**: 2026-10-03 12:00
**最终状态**: built
