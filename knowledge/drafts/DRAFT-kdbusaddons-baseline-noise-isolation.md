# DRAFT-kdbusaddons-baseline-noise-isolation — 跨库 tracked 基线噪声精确隔离-完整复验-原样恢复

> **Contributor**: pc1-8 | **Status**: DRAFT | **Updated**: 2026-08-31
> **Severity**: medium | **Category**: ci / git / ohos / infrastructure
> **Audience**: 共享 build_in_harmonyos 仓库内所有在恰逢他库合入跟踪垃圾文件时跑 finish/W3 的配方
> **Stem**: DRAFT-kdbusaddons-baseline-noise-isolation（与同名 .kv 配对，字段逐一对齐）

## Scope
当 finish 的 W3 本地 CI 模拟被 junk_check JC1/JC5 报告的"Junk Files: N"阻塞，且被拦文件全部位于**其他库的已跟踪路径**（与当前库 diff 无关）时，采用"精确隔离（git rm --cached，磁盘不改）→ 完整自然 finish/W3 → 原样恢复（git add）+ 逐项证明一致"的处理流水线；不做删除/白名单/改他库/重跑掩盖。

## 背景（原始失败，kdbusaddons 6.29.0 r05 实测）
- W3 `build_and_test.sh` 的 `junk_check.sh` 以 **full 模式**对整仓 `git ls-files` 扫描（`检查模式: full (40764 个文件)`）。
- JC1 拦截模式命中 3 个**其他库已跟踪**文件：`archives/i/isa-l_crypto/2.26/conandata.yml.orig`、`archives/m/middleclass/4.1.1/conandata.yml.ghfast-bak`、`archives/s/swift-corelibs-blocksruntime/6.3.3/.staging-verified`；JC5 报告 1 个未登记隐藏文件（同上 `.staging-verified`）。
- 输出：`Junk Files: 2 / JC_RESULT=fail / JC_ERRORS=2 / L0_RESULT=fail: junk_check failed / [fail] JC: junk files detected — blocking build`，`L1-L5 skip: blocked_by_JC`。
- 三个文件均由他库功能提交带入（`feat(isa-l_crypto) 2.26`、`feat(middleclass) 4.1.1`、`【积分赛】feat(swift-corelibs-blocksruntime) 6.3.3`），与本库 diff 完全无关 → 归为**跨库 tracked 基线噪声**。

## 诊断判定（先证明是基线噪声，再动手）
```bash
# 当前库 diff 是否触碰被拦路径？（应为空）
git status --porcelain -- <被拦路径>
# 被拦文件是否已跟踪、来源何方？
git ls-files --error-unmatch <被拦路径>
git log --oneline -1 -- <被拦路径>
```
kdbusaddons r05 实测：三个路径 `git status --porcelain` 均为空、`ls-files` 均为 tracked、来源 commit 均在 main 历史（2026-08-27 早于本任务）→ 确认无关基线。

## 解决方案（步骤与证据链）
1. **隔离前快照 provenance**：对每个被拦路径记录 git 状态、`git ls-files -s` index blob、`git hash-object` worktree sha1、`sha256sum`、模式、来源 commit。
   - kdbusaddons r05 实测：`conandata.yml.orig` blob `22ed1cf08060dec5f149cda6f771309a1fa7a7c5` / sha256 `d62412e1…`；`conandata.yml.ghfast-bak` blob `ed6b28d565fc72f8201873e48f67e33a9aa5334f` / sha256 `226348ef…`；`.staging-verified` blob `e69de29b…`（空文件）/ sha256 `e3b0c442…`。
2. **精确隔离**：`git rm --cached --quiet <f1> <f2> <f3>`（磁盘文件原样保留，仅移出跟踪状态；`.staging-verified` 等被 .gitignore 拦的路径在恢复时需 `git add -f`）。
3. **完整自然 finish/W3**：`python3 scripts/ohc-run.py finish kdbusaddons 6.29.0 built`（完整流程，非仅 `--resume`）。JC 无拦截：`JC no junk files detected / JC_ERRORS=0`；随后 conan create 成功、test_package 2/2、`Build Summary Success:1 Failed:0`、`.ci-result.json exit_code=0`。
4. **原样恢复**：`git add -f -- <f1> <f2> <f3>`。
5. **逐项证明一致**：恢复后 `git ls-files -s` index blob == 隔离前快照 blob == `git hash-object` worktree sha1；`sha256sum` 一致；模式 100644；`git status --porcelain -- <三路径>` 为空（clean/tracked）。

## 适用边界
- **适用**：被拦文件全部为**他库已跟踪**、当前 diff 未触碰的基线噪声；配方的真实构建/测试本身可通过。
- **不适用**：被拦文件属于当前库自身新增/修改；或隔离后 W3 仍有当前库真实失败（配方缺陷/依赖缺失/网络）——此时必须停止返工、按外部首错如实回报，不得用本方法掩盖。
- **任务约束**：remote_authorization=none 时不得 commit/push/PR/Issue/远端 CI/Conan remote；不得访问 `/mnt/e` 模板；不得把日志/构建产物/他库文件/三处基线文件纳入当前库知识草稿。

## 验证（verification / evidence）
- `git -C <worktree> rev-parse --abbrev-ref HEAD` / `rev-parse HEAD`：分支与 HEAD 与任务一致（kdbusaddons: `feat/kdbusaddons-6.29.0` / `bbbf8b44ec9a…`）。
- `git -C <worktree> status --porcelain | head`：仅当前库目录（untracked）+ 仓库既有 libXext 差异；无他库/基线改动。
- `.ci-result.json` 关键字段：`{"exit_code": 0, "step": "W3_local_ci", "log_sha256": "b4ceb0b5f181ea…"}`。
- `w3-local-ci.log`：`L0_RESULT=pass`、`Build Summary Success: 1 Failed: 0`、`All packages built and tested successfully`。

## 失败状态（failure state）与恢复条件
- 恢复条件：恢复后若任一文件的 index blob / worktree sha1 / sha256 / 模式 / 跟踪状态与隔离前快照不一致，或 git status 出现他库残留 → 视为隔离失败，立即按快照复核并如实回报，不得进入下一步。
- 终止条件：隔离后 W3 仍失败的根因若属当前库自身（非基线噪声）→ 停止返工回报外部首错；由分析端/后续任务决策，禁止新增轮次或掩盖。

## 关联查重（增量说明）
- 已检索 `knowledge/**`：baseline noise（0）、git rm --cached（0）、w3_local_ci（0）、tracked junk/JC1/JC5（仅 `DRAFT-jc6-origin-main-stale-ref`，为 JC6 三点 diff ref 过时陷阱，不覆盖本主题）、atomicity/isolation（E260 native-image fd 等，主题无关）、predl/URL 截断（`DRAFT-E212-ci-predl-regex-pypi-url`、`DRAFT-ci-mirror-fallback-conandata-restore`，属 predl 下载/改写恢复，不覆盖"跨库 tracked 基线隔离"）。
- 结论：本条目为新增增量（新 stem 无冲突），主题、error_signature、root_cause、solution、verification、适用边界、failure state 与本 .kv 逐字段对应。

## Source
- 事件：kdbusaddons 6.29.0 round-5（`finish_w3_baseline_isolation`），任务 `kdbusaddons-6.29.0-r05-w3-baseline-noise-isolation-pc1-8-20260831-134841`。
- 命令/日志：`w3-local-ci.log`（full 模式 JC 扫描、JC1/JC5 命中、隔离后 JC 通过）、`conan-create.log`、`conan-verify-report.md`、`.ci-result.json`。
- provenance 快照：`/storage/Users/currentUser/tmp/oh-exec/kdbusaddons_r05_baseline_snapshot.json`。