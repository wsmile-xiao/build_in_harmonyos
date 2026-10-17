# pasco/20040505 W4 独立审计（r1）— z74-pasco-w4

- 绑定 HEAD：**`00a84ae2141d588c2cc67f4d17419abd7165bde5`**（`git rev-parse HEAD` = 本地分支 ref = `git ls-remote origin feat/pasco-20040505`，三者同一；`git status --porcelain -- archives/p/pasco` 空）
- 坐标：B 机 `~/qzy/主理-74-pasco-20040505`，归档 `archives/p/pasco/20040505/`
- **判决：pass（P0=0 / P1=0 / P2=1 / P3=7）**
- 取证落盘：`~/tmp/uc2/z74-pasco-w4/{coord,f1..f16}.txt`

## A. W2 结构 / 配方正确性 — PASS

| 判据 | 一手读数 |
|---|---|
| 入库文件集 | `git ls-files archives/p/pasco` = 12 文件；`git diff --stat upstream/main...HEAD` = `12 files changed, 611 insertions(+)`；与 `w3-local-ci.log:71 检查模式: incremental (12 个文件)` 三方对齐 |
| 补丁登记 | `conandata.yml:10-13` `patches:` → `patch_file/patch_description/patch_type: "portability"` 齐 ⇒ 无漏登记 |
| source.url | `conandata.yml:7` = `https://downloads.sourceforge.net/project/odessa/Pasco/20040505_1/pasco_20040505_1.tar.gz`（官方 FRS canonical，带完整子目录） |
| 禁址扫描 | 对 12 个 tracked 文件 `grep -Hn "deb.debian.org\|file://\|ohpcd"` → **仅 1 命中**：`notes.md:20` 的池件交叉核验表格（规则允许出现在 notes 核验叙述里）；无 `file://` |
| 配方面 | `conanfile.py:30 package_type="application"`、`:52-53` 从 `tools.build:compiler_executables` 取 CC（R33）、`:57 make -C src install -j1`（R9）、`:66 bindirs=["bin"]`、`:37-39` 无 requires |
| 结构对照 | 与已合入 `archives/v/vamps/0.99.2` 同文件集（版本级无 README，软件级有 README+commands.json）⇒ 不缺件 |

## B. ★最大风险项：补丁是否"顺手重写整个上游 Makefile" — **假设不成立，无 P1**

实读三件：`~/tmp/builds/pasco-20040505.orig/src/Makefile`（10 行全文）、`patches/0001-Makefile.patch`（HEAD 版）、`.work/src/Makefile`。

- 补丁形状：`@@ -1,10 +1,10 @@`，**只有 2 行 -/+**（原第 4、7 行），`all:` / `installwin:` / `clean:` 与 `clean: ` 的尾随空格全部作为上下文行原样保留 ⇒ 就地最小改写，**不是整文件替换**。
- ① 上游有没有 `override` / CC/CFLAGS/LDFLAGS 变量：**都没有**。orig 实物里编译器是字面量 `gcc`（`gcc -o pasco pasco.c -lm -lc;cp pasco ../bin`），`override`/`$(CC)`/`$(CFLAGS)` 计数 0（`conanfile.py:6-7` 文档串与 `notes.md` 源码修改段同口径，我逐字核过 orig）。⇒ 委托方设想的"命令行变量本就必然覆盖文件内赋值，所以整文件替换是扩大改动"这条推理链**在本包前提不成立**：编译行里没有变量可被覆盖，不打补丁就编不出来。补丁是必需项，且已收敛到最小。
- ② 无需整文件替换的理由 ⇒ 不触发披露义务；但 notes 仍逐字披露了上游 10 行全文、两个改动点、未删目标清单、`pasco.c` 未改一字节（sha256 `9ffa61f8…`）。
- ③ `manifest.yaml:43-46` `patch_classification` 与实物一致（`method: per-file-difflib` ↔ `type: auto`）；仅 `platform_only: True` 有一处偏差 → R1-3（P3）。
- 前任 `z74-07-refine.sh` 的整文件 printf 只作用于**探索目录**，最终入库补丁未继承其形状（`notes.md` 源码修改段末两条已自陈这段演化并声明"没有整文件替换"——我按实物复核为真）。

## C. W3 证据自洽 — PASS

| 判据 | 实算 |
|---|---|
| `log_sha256` | `.ci-result.json:9` = `3eea028579861114c50ec78901f525355cdb1cc4c38369675fd97305e3dac6a7`；`sha256sum reports/w3-local-ci.log` = **同一 64 位串** ✅ |
| 真构建证据 | `w3-local-ci.log:170 pasco/20040505: Building from source`、`:177 pasco/20040505: Calling build()`（`:156/:220/:224` 的 `- Cache` 未被当证据用）✅ |
| 门禁判决 | `:90 JC_RESULT=pass`、`:269 ASSERTIONS=27 PASS=27 FAIL=0`、`:285-289` L0/L1/L4/L5 pass、L2 skip |
| conan-create.log | 实算 sha256 `27ee606be9cee18e3d7f3a9433f1ffa46f2466127cd99abb4b19c465eb801396` = notes 声明值 ✅；`wc -l`=148、14215B/8232B；notes 声明的 `:100 起逐条 ok`（实算首条 `ok [noargs] exit=254` 就在 :100）、`:146 ASSERTIONS=27`（实算同位）✅ |
| HEAD 绑定 | **`.ci-result.json` 全文 10 行内无任何 commit/HEAD 字段**；timestamp 02:03:58 早于提交 00a84ae（02:10:09）。缓解：`git show --stat 00a84ae` 只改 `notes.md` ⇒ HEAD 树里 11 个构建相关文件与 W3 输入逐字节同一 → 记 R1-2（P3，措辞口径） |
| 入库口径 | `reports/`、`.ci-result.json`、`ci-metadata.json`、`.build-closed`、`.conan-verified`、`.handoff.json` **全部未被 git 跟踪**（与 vamps 同一 .gitignore 口径）⇒ 不入 PR，不算缺陷 |

## D. 测试质量（rule4/rule12）

- **27 条逐条数过**（test.sh:32-81）：4+9+3+3+3+2+3 = **27**，与 `MANIFEST.yml:30 assertion_count: 27`、w3:269、conan-create.log:146 同源一致。
- **真执行产物**：`run()` 直接 exec 打包后的 `pasco`，断退出码 + stdout 内容 + 分隔字段数（`nf()` 用 awk 数字段）；**无编译期断言冒充运行期**。CI 侧另有独立佐证：`w3:279-281 [sabotage] bin/ moved away → [ok] L1e: Negative test confirmed — test genuinely depends on pasco`（R34 破坏性反向测试）。
- **上游测试申报**：`MANIFEST.yml:11 upstream_check_command: ""`、`:14 upstream_test_in_build: false`、`:18 upstream_tests: []` ⇒ 申报 **0 条**，全文无"上游测试全通过"话术；依据在 notes（Makefile 仅 all/install/installwin/clean、发行包 4 文件无测试源）。
- **合成输入不伪造**：`gen_index_dat.py` 文档串 1-20 行列出构造依据取自 `src/pasco.c` 的偏移（0x18 版本串 / 0x1C filesize / 0x20 hashoff / record+0x34/0x38/0x3C/0x44），产物被 pasco 实测解析为 v5.2。
- **失败会不会被吞**：`test.sh:84 [ "$fail" = 0 ] || exit 1`、`:30` 样本生成失败即 `exit 1`、无 `set -e` 掩盖 ⇒ 不会。
- **timeout 兜法判定（委托方点名）：不会把真失败算成通过**。`run junk 124 timeout 5 pasco …` 的期望值 124 **只能由 timeout 杀进程产生**；二进制若自行退出（包括正常 0）该断言立刻 FAIL。正向路径另有 `run valid 0` 独立断言 ⇒ 若产物整体不可执行，case 2 必红。残余弱点两条：该用例断的是"缺陷仍在"（上游若修好会翻红，方向安全）；`command -v timeout` 缺失分支只 `echo SKIP` 不改 fail ⇒ 换机时可能实跑 24 条而表仍报 27 → R1-5（P3）。
- **鸿蒙特有面 ≥1 条**：test.sh 内**无显式标注鸿蒙特有的断言**；OHOS 专属处理在 `test_package/conanfile.py:24-26`（`CONFIG_SHELL` 兜 `/data/service/hnp/bin/bash`，因 `/system/bin` 的 mksh 不能 exec ELF），该路径判错则整个 test() 失败 ⇒ 属**隐式在测**。判 R1-4（P3，建议补 1 条显式断言），不判 P1：无虚报、且 CI 的 L2 smoke 如实报 `skip` 未假绿。

## E. harness 回写地雷 — PASS（回写风险本体记 P2）

- **`guard` 不是 pending**：`manifest.yaml:46 guard: 'fresh_extract_patch_p1_cmp_identical'`；`:26 patches_applied: - 0001-Makefile.patch` 非空；`:44 type: auto`、`:45 platform_only: True`。
- 全包占位符扫描 `grep -rniE "pending|TODO|占位|xxxx|FIXME" .`（排除 reports/）→ 4 命中，**全部在 notes.md**（引用 harness 占位符名的复原记录）⇒ **残留占位符 0**，逐条判属完成。
- **R1-1（P2）地雷未结构性拆除**：盘上三枚 harness 备份证明回写过两次 —— `.patch-backup-20260927005738/`（16 行、md5 4604c6fe…，头 `--- a/Makefile`，且当年还把 `clean: ` 尾随空格改掉）、`.patch-backup-20260927015147/`（md5 42f33434…，头仍是 `a/Makefile`），现文件 md5 892dfbcb…、mtime 01:55:26；`diff -u 015147→现文件` 唯一差异就是头两行 `a/` → `a/src/`。notes 记录当年 G2 FAIL 的第一条真实错误 = `conan-create.log:97 … source/target file does not exist:` + `--- b'a/Makefile'`。⇒ **当前实物正确，但正确性依赖 git 之外的 worktree 本地状态**（探索目录已改成 `src/` 布局）。任何再跑 `finish`/`refresh-patch` 之后必须 `head -2 patches/0001-Makefile.patch` 复验为 `a/src/Makefile` 才可让渡/提审。
- `platform_only: True` 的真假由证据定：`gcc`→`$(CC)` 半是平台必需（本平台无 gcc 无 cc），`mkdir -p ../bin` 半按 notes/README 自陈是**任何平台都成立**的上游缺陷 ⇒ 整体标 platform_only 偏乐观 → R1-3（P3，可辩护，非占位符，presubmit/AI 的 pending 硬门不会命中）。
- `.patch-backup-*` 未入库 ⇒ PR 干净；仍是 `git add` 误手风险 → R1-7（P3）。

## F. B 证据三问（**只交证据，不下 B 结论**）

检索全部为一手 grep，命令与命中数见 `audit-result-r1.json → b_evidence.queries`。

1. **症状同形覆盖？——部分同形、非同因。** 唯一近邻条目 `knowledge/drafts/DRAFT-libfec-refresh-patch-hmdfs-dryrun-placeholder.{kv,md}`：`error_signature`(:10-12) 含 `source/target file does not exist:` —— 与 pasco 实错**逐字同签名**，`trigger_tool`(:8) 同为 `refresh-patch|conan|patch`；但其 root_cause(:23-31) 是 "HMDFS 上 dry-run 真实创建 0 字节占位 → 新增文件被误判为修改文件 → 头从 `--- /dev/null` 退化成 `--- a/`"，pasco 是"探索目录布局与归档布局不一致（文件在根 vs 在 `src/`）→ refresh-patch 把已正确的 `a/src/Makefile` 刷回 `a/Makefile`"。另 `archives/a/abiword-plugin-clarisworks/3.0.8/notes.md:37` 与 `-mswrite/3.0.8/notes.md:37` 记录过同症状（"生成 `a/` 前缀补丁，patch_ng 无法应用，W3 conan create 阻塞"，引 E258），因也是 dry-run 污染 orig。检索词 摊平/扁平/补丁头/patch header/a/src/ 在 knowledge 共 41 命中（18 个文件，逐条读过），**无一命中"布局不一致"这一因**。
2. **处方同一条？——否。** libfec 的 `rec_priority: 1 = remove-orig-placeholder-before-refresh-patch`，verification_cmd 要求头必须 `--- /dev/null` + 删 .orig 占位；对 pasco 无效（pasco 的目标文件在 orig 中**存在且被修改**，正确头是 `a/src/Makefile`，删占位不改变任何事）。pasco 实际处方 = 探索目录改 `src/` 布局 + 复原补丁 + 重跑 finish。abiword 是第三条处方（放弃补丁、改 `export_sources()`）。三条互不覆盖。
3. **边界排除？——是。** libfec 自身 `affected_scope`(:32-34) 限定 "为**新增源文件（orig 中不存在）**生成补丁" 且需占位污染前置 ⇒ 明确把 pasco（修改已存在文件）排除在外。pasco 另一面（裸 Makefile + 字面量 gcc + CLI + R38 + 消费者测试）已由 `knowledge/DRAFT-cronutils-1.1-raw-makefile-ohos-cli-signing.kv`(:15,:36-41) 与 `archives/d/dextractor/1.0.1/notes.md:29`、`archives/c/convlit/README.md:13`、`archives/m/malbolge/README.md:19` 覆盖 ⇒ **不构成新机制**；且本包未触发其 .codesign 处方也能在 OHOS 真跑起二进制（w3:278 L5 pass + 27 断言在 conan create 内执行）。
4. 交付物现状：`ls knowledge/drafts | grep -i pasco` = **0 命中**；`git diff --stat upstream/main...HEAD` 内 knowledge 文件数 = **0**。登记表 pasco 行 B判定 = "待定（候选=create…）"（备注列全文实读）。⇒ 若终判 create，成对 `DRAFT-pasco-20040505-*.{kv,md}` + Issue 回填号仍是**未交付项**。

## 问题清单（按严重度）

| ID | 级别 | 一句话 | 位置 |
|---|---|---|---|
| R1-1 | **P2** | refresh-patch 回写地雷未结构性拆除，修复体在 git 之外 | patches/0001-Makefile.patch:1-2 + 3 枚 .patch-backup-* |
| R1-2 | P3 | .ci-result.json 无 HEAD 字段，"绑定 HEAD" 靠时间戳+差分推断 | .ci-result.json:1-10 |
| R1-3 | P3 | platform_only=True 对 mkdir 半 overstated | manifest.yaml:42-46 |
| R1-4 | P3 | 无显式"鸿蒙特有"断言（隐式经 CONFIG_SHELL 覆盖） | test_package/test.sh:32-81 |
| R1-5 | P3 | 无 timeout 时静默少跑 3 条而申报数不变 | test_package/test.sh:74-81 |
| R1-6 | P3 | commands.json `binary:false` 与 ARCHIVE-SPEC 示例/同类 CLI 相反 | commands.json:9 |
| R1-7 | P3 | patches/ 下三枚备份目录（未入库） | archives/p/pasco/20040505/patches/ |
| R1-8 | P3 | 登记表 pasco 行功能描述写成 "prefetch（SCCA）"，实物是 IE index.dat | 任务登记表.csv pasco 行备注列 |

## 收口前仍欠（≤3 件）

1. **R1-1**：把"任何 finish/refresh-patch 重跑后 `head -2` 复验补丁头为 `a/src/Makefile`"变成让渡/提审前硬动作。
2. **B 判定终判 + 草稿落地**：三问证据显示既有条目按自身 scope 排除本情形、处方也不同一条；若判 create，PR 内目前 0 个 knowledge 文件，DRAFT 成对件与 Issue 均未交付。
3. **PR 出厂对账整段未审**（尚无 PR 号）：标题前缀、正文 3+2、任务 9321 平台回读、`$P presubmit` 四项都要在 PR 建好后补一轮。

---

## 追加（判决件写完后实测；只读窗无写表权限，仅上报）

- 收尾复验工作树时发现**非本包脏文件**：全仓 `git status --porcelain` 输出含
  `M archives/l/libXext/README.md`、`M archives/l/libXext/manifest.yaml`、`?? .build-cache/`。
- 本包作用域仍干净：开工第一步的 `git status --porcelain -- archives/p/pasco` 为空，HEAD 仍是
  `00a84ae2141d588c2cc67f4d17419abd7165bde5`（收尾再读一次同值）。
- 定性：**不是 pasco 归档缺陷，未计入 counters**（他包资产，本窗未动、不回滚、不清理），但属 **PR 纯度风险** ——
  pasco 分支 `feat/pasco-20040505` 所在工作树里躺着 libXext 的未提交改动，任何 `git add -A` / `commit -a` 类误手
  会把第二个软件归档带进本 PR，直接违反「一个配方 PR 只包含一个软件归档」。与 R1-7 同一失效面。
- 处置建议：主理-74 在建 PR 前先确认这两枚 libXext 改动的归属窗口并按 §6/§7 处理（本审计窗不代为搬运或清理）。
