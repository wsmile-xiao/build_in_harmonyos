# DRAFT-dr_mp3-0.7.2-baseline-noise-isolation — dr_mp3 0.7.2 全仓 W3/JC 扫描命中共享基线噪声的临时索引隔离复验

> **Contributor**: pc1-75 | **Status**: DRAFT | **Updated**: 2026-08-31
> **Severity**: high | **Category**: ohos / ci / infrastructure
> **Audience**: 在共享 build_in_harmonyos 仓库执行 W3/finish 的新库执行端（R02/R03 基线噪声豁免模式）

## 问题签名与触发条件

问题签名：

```text
Junk Files: 2
JC_RESULT=fail
L0_RESULT=fail: junk_check failed
L1/L2/L4/L5_RESULT=skip: blocked_by_JC
Pass rate: 0.0% (0/1)
Failed packages: dr_mp3/0.7.2 (JC gate)
```

命中文件不属于当前库（dr_mp3）：

- JC3：`archives/g/goaccess/1.10.2/ncurses-headers.tar.gz`（被跟踪的 tarball）
- JC5：`archives/s/scudo-malloc/19.1.6/.manifest-complete`、`.progress-closed`（未登记隐藏工作流标记）

触发条件：当前库分支从 origin/main 新建、零提交（HEAD == origin/main，三点 diff 为空）时，
`ci/scripts/junk_check.sh` 兜底进入 **full 模式**（`git ls-files` 整仓扫描），命中 origin/main
上游历史遗留的无关库基线文件。

## R02 首错

R02（`dr_mp3-0.7.2-r02-finish-and-test-ledger-pc1-75-20260831T001330Z`）在 finish 的
[5/10] W3 本地 CI 模拟步骤被 JC full 扫描拦截，dr_mp3 自身 Conan（G1-G4+L2/L4/L5）、
test_package 11/11、消费者验证、W4 审计全部通过，唯一失败位于共享基线噪声。R02 按
"外部首错"规则回报阻塞归属，未重跑掩盖、未修改其他库文件。

## 三条精确基线路径及其来源/HEAD blob/SHA-256

| 路径 | origin/main 来源 | HEAD blob | SHA-256 |
|---|---|---|---|
| `archives/g/goaccess/1.10.2/ncurses-headers.tar.gz` | commit 2d5de502d8（feat(v12.13)...） | `b154073f94a4637ead69f8628bc1f2588acbe478` | `bf58efee849debcfa56ce02f2a099aa25638de6bed90f356fc1018aac59d5e11` |
| `archives/s/scudo-malloc/19.1.6/.manifest-complete` | commit 2d5de502d8 | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391`（空 blob） | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `archives/s/scudo-malloc/19.1.6/.progress-closed` | commit 2d5de502d8 | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391`（空 blob） | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

三文件均在 origin/main tree 中与工作树无差异（`git ls-tree origin/main` 实证 blob 一致，
`git status --porcelain` 干净），属无关历史基线，非 dr_mp3 引入。

## 根因与归属

`ci/scripts/junk_check.sh` 判定检查范围（约第 35-44 行）：

1. 有 `pr.diff`（或 `JUNK_PR_DIFF`）→ `prdiff` 模式（仅 PR 文件）。
2. 否则三点 diff `origin/main...HEAD` 非空 → `incremental` 模式。
3. 两者皆空（本地新库分支尚未提交）→ **full 模式**：`CHECK_FILES=$(git ls-files)`（整仓所有已跟踪文件）。

full 模式下 JC3 拦截 `*.tar.(gz|xz|bz2|tgz)`（非 prebuilt）、`/packaging/.*\.tar`；
JC5 拦截 `archives/.*/\.[^/]+$` 且不在 `JC5_ALLOWED` 白名单的隐藏文件。
仓库 main 历史预存的其他库 tarball/未登记隐藏标记会被整仓扫描命中，阻塞任何零提交新库。
归属：**共享基线噪声（origin/main 上游遗留、其他库文件），非当前库缺陷、非执行端环境缺陷**。

## 隔离 / 自然 finish-W3 复验 / 恢复审计方案

1. **取证**：逐项记录路径、origin/main 来源 commit、HEAD blob、工作树 Git 状态、文件类型、SHA-256。
2. **临时精确索引隔离**：`git rm --cached <3 文件>`——仅摘除索引，工作树文件保留、内容零修改；
   不修改/删除/提交其他库文件。隔离后 `git ls-files` 三文件计数=0，junk_check 落入 prdiff/full 之外的
   实际扫描不再命中 → `JC_RESULT=pass`。
3. **完整自然运行 finish/W3**：不设观察窗口、不以超时当失败、不重跑掩盖当前库首错。
4. **恢复**：`git add <3 文件>`（tarball 命中 `.gitignore` 时用 `git add -f`，空文件直接 add）恢复索引；
   工作树文件从未移动，恢复后核对 SHA-256、HEAD blob、Git 状态逐项一致。
5. **终核**：`git ls-files` 三文件计数=3、`git status` 对三路径干净、`git diff HEAD` 为空。

## R03 真实验证结果

- 隔离前取证：三文件 SHA-256 记录（取证日志 `/storage/Users/currentUser/tmp/r03-baseline-forensics.log`）。
- `git rm --cached` 隔离后：`git ls-files` 三文件计数=0；junk_check `JC_RESULT=pass / JC_ERRORS=0`。
- finish 10 步自然运行：W3 本地 CI 模拟通过（`L0/L1/L4 pass`、`L2/L5 skip`），
  `.ci-result.json` 写入归档（exit_code=0，sha256 `22d2603a4aef4714491a665ad5777a99b8be68e7e2f441e5ac35b1263688d780`）。
- `git add -f` 恢复后：HEAD/INDEX blob 逐项一致（`b154073f94a4637ead69f8628bc1f2588acbe478`、
  `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391`×2）；SHA-256 与取证明细逐项相同；`git status` 干净；
  `git ls-files` 三文件计数=3。
- 终态：0 commit、框架零改动、仅 `archives/d/dr_mp3/**` 候选；结论 `baseline_noise_exempted`。

## 适用范围与不适用条件

适用范围：

- 新库分支零提交（HEAD==origin/main）、junk_check 落入 full 整仓扫描、误报源于其他库已跟踪的
  基线 tarball/隐藏标记、且该库自身 Conan/test_package/消费者/W4 已真实通过。
- 隔离仅为临时、仅作用本地索引、恢复后 SHA-256/blob/Git 状态与隔离前逐项一致。

不适用条件：

- 当前库自身真实构建/测试/配方失败（不得以基线噪声名义掩盖，属 `quality_rework_required`）。
- 命中文件属于当前库自身 diff/staging/commit（W2 原子性违规，不得豁免）。
- 任务未授权基线隔离复验的场景（须任务正文明示 baseline-noise-exempted 或等效治理授权）。

## 禁止边界

- ❌ 修改、删除、暂存或纳入当前库 PR 范围：`archives/g/goaccess/1.10.2/ncurses-headers.tar.gz`、
  `archives/s/scudo-malloc/19.1.6/.manifest-complete`、`archives/s/scudo-malloc/19.1.6/.progress-closed`。
- ❌ 修改共享框架或其他库文件（如 `junk_check.sh` 白名单登记须由框架维护者单独 PR）。
- ❌ 伪造 `.ci-result.json`、把不可运行的上游测试入口伪写为通过、以基线噪声掩盖当前库首错。
- ❌ 把隔离当永久状态（完成后必须恢复，保持 PR 原子性与零污染）。

## 维护方后续治理条件

- 由 goaccess / scudo-malloc 归档责任方或框架维护者处理：goaccess tarball 改外部下载/移出 tracked
  scope/登记 prebuilt 豁免；scudo-malloc 两个隐藏工作流标记在 `junk_check.sh` `JC5_ALLOWED` 登记
  或清理对其无意义的空标记。治理完成后新库 W3 不再需要隔离豁免。

## 查重差异

| 既有条目 | 主题 | 与本条差异 |
|---|---|---|
| DRAFT-jc-full-scan-baseline-noise-exemption（pc3-22/libutf8proc） | JC full 命中基线垃圾→隔离豁免 | 同主题但为 libutf8proc 事件、来源/证据不同；本条为 dr_mp3 R02/R03 具体三路径与实测证据 |
| DRAFT-jc-full-mode-git-index-isolation（pc3-24/eigen3） | git 索引隔离/恢复工序 | 工序一致，但其命中为 `.orig/.ghfast-bak/.staging-verified` 且含 predl 陷阱；本条 goaccess/scudo 三路径 + `git add -f` 场景 |
| DRAFT-junk-full-mode-zero-commit-baseline-noise（pc1-40/recastnavigation） | 零提交 full 误报 goaccess tarball | 同 goaccess tarball 但用 prdiff 窄范围隔离；本条用 git rm --cached 索引隔离，命中三文件（tarball+两空标记） |
| DRAFT-jc-junk-baseline-noise（libvncserver） | 同上类 | 同类不同库事件证据 |
| DRAFT-jc6-origin-main-stale-ref | JC6 origin/main 引用过时 | 不同门禁/根因（ref 过时 vs 基线垃圾） |
| knowledge/graph 正式条目 | （grep 检索 0 命中） | 无正式条目覆盖 |

结论：dr_mp3 专属三路径隔离复验完整证据链无既有草稿/正式条目覆盖，需要新增本对草稿。

## 证据（Evidence）

- R03 取证日志：`/storage/Users/currentUser/tmp/r03-baseline-forensics.log`
- R03 W3 日志：`archives/d/dr_mp3/0.7.2/reports/w3-local-ci.log`（sha256 `389f3414be2d6ac216e36ae9a5253d66969e9f425399416ac853894172763883`）
- R03 `.ci-result.json`：`archives/d/dr_mp3/0.7.2/.ci-result.json`（sha256 `22d2603a4aef4714491a665ad5777a99b8be68e7e2f441e5ac35b1263688d780`，exit_code=0）
- R03 delivery preview：`archives/d/dr_mp3/0.7.2/reports/delivery-preview-r03.json`（conclusion=baseline_noise_exempted）
- 上游测试台账：`archives/d/dr_mp3/0.7.2/reports/upstream-test-ledger.md`（3/3 真实尝试、0 通过、如实留证）

## Source

- 门禁脚本：`ci/scripts/junk_check.sh`（35-44 模式判定、126-144 JC3、173-190 JC5、`JC5_ALLOWED`）
- 事件：dr_mp3/0.7.2（pc1-75）R02 finish [5/10] W3 被 JC 拦截 → R03 三文件索引隔离+自然 finish-W3+恢复，前后 SHA-256/blob/Git 状态逐项一致，结论 `baseline_noise_exempted`
- 关联库：dr_mp3 0.7.2（header-only MP3 解码库，dr_libs 官方 tag mp3-0.7.2，commit 547c211a87a06a42bf62c1366616aa14b57dd429）
