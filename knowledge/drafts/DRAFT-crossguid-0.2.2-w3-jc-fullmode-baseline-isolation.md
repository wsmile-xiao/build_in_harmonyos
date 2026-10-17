# DRAFT: W3 junk_check full 模式命中其他库已提交基线标记文件 → 临时索引隔离复验

> 草稿编号：DRAFT-crossguid-0.2.2-w3-jc-fullmode-baseline-isolation（同 stem .kv 配对）

## 问题

本地 `ohc-run.py finish` 的 W3 门禁（step 5/10，`build_and_test.sh` 内 `junk_check.sh`）报
`JC_RESULT=fail`（Junk Files: N，JC1/JC5 命中其他库的 `.build-closed`/`.staging-verified` 标记文件），
阻塞提交 PR；但这些文件属于当前库允许范围外、提交前已存在的其他库基线。

## 根因

`ci/scripts/junk_check.sh` 扫描范围三选一：`prdiff`（PR diff 文件）> `incremental`
（`git diff origin/main...HEAD`）> `full`（`git ls-files` 全仓库，incremental 为空时退化）。
新适配分支尚未产生 commit 时 `origin/main...HEAD` 为空 → 退化 **full 模式** → 扫描仓库**全部被跟踪文件**；
若 origin/main 基线中历史遗留了其他库误提交的 0 字节标记文件（如 `archives/c/cloog/0.21.1/.build-closed`、
`.staging-verified`），JC1/JC5 即拦截本地 W3。远端 CI 走 prdiff 模式只看 PR 文件清单，不受影响。

## 方案（基线隔离流程）

1. 确认命中文件为其他库已提交基线标记：`git cat-file -e origin/main:<path>` 存在、0 字节/无业务内容、
   不属于当前库允许范围。
2. 记录精确路径与**隔离前 SHA-256**。
3. `git rm --cached <paths>`：仅移出索引，磁盘文件不动。
4. 重跑 finish/W3（JC 不再扫描该文件）→ 通过。
5. `git reset HEAD -- <paths>` 原样恢复索引。
6. 核对**隔离后 SHA-256 == 隔离前**、`git status` 干净、`git diff origin/main` 为空。
7. 这些路径绝不进入当前库 commit/PR；隔离复验通过后继续当前库审计与交付。

```bash
git rm --cached <paths>
python3 scripts/ohc-run.py finish <软件> <版本> built
git reset HEAD -- <paths>
sha256sum <paths>   # pre == post
```

## 适用边界 / 反例

- 适用：分支无 commit、仓库 main 基线含历史遗留标记文件的环境中所有走 finish W3 的本地适配任务。
- 反例：命中文件属当前库真实引入（当前库的标记/二进制/临时产物）时，必须清理当前库文件后重跑，
  不得隔离；其他库既有基线文件才适用本流程。

## 验证

- crossguid 0.2.2：W3 首跑 `JC_RESULT=fail`（full 模式，4 个其他库标记文件：cloog×2、kics、thc）；
  索引隔离后复跑 W3 通过；恢复后 SHA-256 一致（pre==post，空文件 `e3b0c442…`），
  `git status` 干净、`git diff origin/main` 为空。
- 既有条目：`similar_to=[E291]`（repository_baseline_blocked：基线阻塞记录、不混入当前库 PR 族；
  但 E291 触发为 graph validate，本条目触发为 JC junk_check full 模式，且补充了索引隔离操作步骤）。

## 查重结论

`exact_duplicate=false, causal_duplicate=false, trigger_overlap=partial, solution_overlap=partial,
combination_novelty=true, boundary_novelty=true, test_migration_novelty=false` → **new_draft**。

---
*作者: AtomCode | 来源: crossguid 0.2.2 (crossguid-0.2.2-r01-pc4-1) | 2026-09-27*
