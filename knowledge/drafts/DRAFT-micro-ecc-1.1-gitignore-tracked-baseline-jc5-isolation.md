# DRAFT-micro-ecc-1.1-gitignore-tracked-baseline-jc5-isolation

> Path B 知识库扩展草稿（由 micro-ecc 1.1 R01 全仓 W3/JC5 基线隔离复验产生，与同名 `.kv` 配对，逐字段一致）。
> 仅为本地知识草稿，不代表任何 PR/commit/push 已成功。

## topic

全仓 W3/JC5 门禁命中「gitignore 但仍被跟踪」的其他库基线文件（如 `.ci-trigger`）时的正确隔离与恢复协议：
gitignore 规则**不豁免**已跟踪文件出现在 `git ls-files` 整仓扫描中，故必须 `git rm --cached` 做索引级隔离，
恢复必须用 `git checkout HEAD -- <path>`（`git add` 会被 .gitignore 拦截）。

## error_signature

```
Junk Files: 1
JC_RESULT=fail
JC5: 1 个 archives 下未登记的隐藏文件:
       archives/u/util-linux-login/2.42.2/.ci-trigger
blocked_by_JC → L1_RESULT=skip → Pass rate: 0.0%
```

## root_cause

junk_check.sh 在 full 模式（零提交新库分支：无 pr.diff、`git diff origin/main...HEAD` 为空）下
按 git index（`git ls-files`）整仓扫描 `archives/.*/\.[^/]+$` 未登记隐藏文件。main 上游其他库遗留的
`.ci-trigger`（util-linux-login 2.42.2 PR 761df452e5 提交，空文件）既被跟踪又命中 `.gitignore:210`
的 `**/.ci-trigger`。关键机制：`.gitignore` 只影响未跟踪文件的 `add` 提示，**不影响已跟踪文件
出现在 `git ls-files`**，因此移出工作树不会消除 JC5 命中；恢复时 `git add` 又被 ignore 拦截。

## durable_solution

1. 取证：`git check-ignore -v <path>` + `git ls-files --error-unmatch <path>` 同时确认
   「gitignore 生效」与「仍被跟踪」；记录隔离前 SHA-256。
2. 隔离：`git rm --cached <path>`（仅动 index），工作树内容经仓库外备份原样保留。
3. 复验：原样重跑完整 `finish <软件> <版本> built`，W3/JC 自然通过（.ci-result.json exit_code=0）。
4. 恢复：`git checkout HEAD -- <path>`（gitignore 拦截 `git add`，checkout 同时恢复 index 与工作树）。
5. 审计：pre_sha256 == post_sha256、`git ls-files --error-unmatch` 恢复跟踪、`git status` 无该路径。

## impact

避免「仅移出工作树却仍被 JC5 命中」的无效隔离（本轮实测两轮失败后才定位到 index 扫描机制），
消除基线噪声对零提交新库分支 W3 的阻塞；恢复命令约束防 gitignore 拦截导致恢复失败。

## recovery_condition

若垃圾文件是当前库自身工作流标记且确实需保留：由框架维护者在 junk_check.sh JC5_ALLOWED 登记
（单独框架 PR）；当前库 PR 不得自行修改框架白名单或清理/提交其他库基线文件。

## evidence_references

- 隔离/恢复命令与 SHA-256 审计：任务 worktree 的 `.ohc/evidence/finish_w3.log`（执行端产物，不入仓）
- pre/post SHA-256：`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`（空文件）
- 路径：`archives/u/util-linux-login/2.42.2/.ci-trigger`（已跟踪；main 提交 761df452e5；不属 micro-ecc 范围）

## similar_to

- DRAFT-dr_mp3-0.7.2-baseline-noise-isolation（同族 JC5 full 模式隔离，但 restore 用 `git add -f`；
  未覆盖 gitignore-but-tracked 形态）
- DRAFT-cute_tiled-1.0.0-cross-library-tracked-baseline-provenance-transport（跨库 tracked 基线证据运输，互补）

## status

draft_pending_review