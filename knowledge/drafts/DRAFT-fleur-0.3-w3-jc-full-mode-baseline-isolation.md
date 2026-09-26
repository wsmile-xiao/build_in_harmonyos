# DRAFT-fleur-0.3-w3-jc-full-mode-baseline-isolation：W3 本地 CI full 模式命中其他库基线状态文件，临时索引隔离复验

> Contributor: pc4-45 | Status: Draft | Updated: 2026-09-26
> Source: fleur 0.3 适配（finish Step5 W3 本地 CI 模拟）
> 对应：`knowledge/drafts/DRAFT-fleur-0.3-w3-jc-full-mode-baseline-isolation.kv`
> 关联：`knowledge/graph/E291.kv`（部分覆盖）、`knowledge/graph/E256.kv`（相关）

## 现象

`ohc-run.py finish <sw> <ver> built` 的 Step5 W3 本地 CI 模拟失败：

```console
❌ build_and_test.sh 失败 (RC=1)
❌ Junk Files: 2
❌ JC_RESULT=fail
[FAIL] JC1: 3 个运行时状态文件被跟踪:
       archives/c/cloog/0.21.1/.build-closed
       archives/c/cloog/0.21.1/.staging-verified
       archives/k/kics/2.1.20/.staging-verified
```

命中文件全部属于**其他库**（cloog/kics），均已在 main 上跟踪（空文件）。
当前库自身没有提交任何运行时标记文件。

## 根因

`ci/scripts/junk_check.sh` 的检查范围选择逻辑：

```bash
JUNK_CHECK_MODE="incremental"          # 默认
if [ -s "$PR_DIFF" ]; then ... JUNK_CHECK_MODE="prdiff"; fi   # CI 走 pr.diff
if 非 prdiff:
    if origin/main 存在:
        git diff --name-only origin/main...HEAD   # 有提交差异才用
        if 空 → JUNK_CHECK_MODE="full"
    else: JUNK_CHECK_MODE="full"                  # 本地无 origin/main
CHECK_FILES=$(git ls-files)                        # full 模式：全仓已跟踪文件
```

本地执行 finish 时（分支无提交差异或无 origin/main），退回 **full 模式**：
`git ls-files` 列出**全仓所有已跟踪文件**。其他库此前把 `.build-closed` /
`.staging-verified` 等运行时标记误合入 main，成为全仓基线噪声 → 当前库被 JC1/JC5
拦截。**删除物理文件无效**——full 模式读的是 git index，不是工作树。

> CI 真实构建走 prdiff 模式（`pr.diff` 文件清单），只检查 PR 涉及文件，
> 提交前已存在的其他库基线文件不会在 CI 中被拦；这是本地 W3 与 CI 的
> 模式差异，不是 CI 会复现的问题。

## 方案：基线隔离复验（四步）

```bash
# ① 记录：路径 + 隔离前 SHA-256
sha256sum archives/c/cloog/0.21.1/.build-closed   # e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855（空文件）

# ② 隔离：索引级移除 + 物理备份
mkdir -p $TMPDIR/baseline-isolate-<sw>
cp archives/c/cloog/0.21.1/.build-closed $TMPDIR/baseline-isolate-<sw>/
git rm --cached archives/c/cloog/0.21.1/.build-closed
# （3 个文件逐个执行，物理文件保留在仓库中供后续恢复）

# ③ 复跑受影响门禁
python3 scripts/ohc-run.py finish <sw> <ver> built   # W3 本地 CI 通过

# ④ 恢复：索引还原 + SHA 核验（被 .gitignore 忽略时须 -f）
git add -f archives/c/cloog/0.21.1/.build-closed
sha256sum archives/c/cloog/0.21.1/.build-closed      # 与①一致
git status --porcelain archives/c/cloog archives/k/kics   # 干净
```

实证（fleur 0.3）：隔离后 finish W3 通过，恢复后 3 文件 pre==post SHA-256
（e3b0c44…），`git status` 对 cloog/kics 为空，PR diff 不含这些路径。

## 适用边界 / 反例

- ✅ 适用：命中文件是**提交前已存在**的其他库基线文件（空标记为主），且
  当前库 diff/staged/PR 不含该路径。
- ❌ 不适用：命中文件属于当前库自身、或属于当前任务引入的文件——那是真实
  JC 问题，必须删除/修复，不能隔离。
- 隔离后仍失败，或文件不满足"既有无关基线"条件 → 按 E291 记录
  `repository_baseline_blocked`（命令/退出码/首错/日志/恢复条件），等待
  仓库维护者清理基线，不得无限重试。
- 框架文件（junk_check.sh / 白名单）只读：不得为绕过 JC 修改白名单。
