# DRAFT-jc6-origin-main-stale-ref — JC6 门禁 origin/main 引用过时陷阱

> **Contributor**: GoliWie | **Status**: DRAFT | **Updated**: 2026-08-21
> **Severity**: high | **Category**: ohos / ci / infrastructure
> **Audience**: 所有新库 CI（基础设施陷阱，非单库）

## Scope
新库 CI 跑 JC6（PR 单软件原子性门禁）前，本地 `refs/remotes/origin/main` 过时会触发 incremental 误报；需用 `git update-ref` 使 origin/main 指向官方 main，恢复 full 模式判定。

## 背景
- CI 的 JC6（`ci/scripts/junk_check.sh`）用三点 diff `origin/main...HEAD` 判定 PR 涉及软件数。
- 当仓库本地 `refs/remotes/origin/main` 过时（落后官方 main），三点 diff 包含官方 main 上其他团队已合入的大量文件 → junk_check.sh 落到 **incremental 模式**，误报 **1321 个包违反 W2 单软件原子性**（涉及软件数巨大，与本次 PR 无关）。

## 模式（步骤）
1. 先核对 `git show-ref`：`refs/remotes/origin/main` 是否 == 官方 main OID（== `refs/remotes/upstream/main`）。
2. 过时时修复：`git update-ref refs/remotes/origin/main refs/remotes/upstream/main`。
3. 修复后三点 diff = 0 文件 → junk_check.sh（line 39-42）进 **full 模式**，line 174-192 JC6 跳过单软件检查。
4. 后续 CI 前保持 origin/main 与官方 main 同步（delivery-refresh 流程；不得自行 delete/sync fork main）。

## 禁止
- 不通过删除候选文件或同步 fork main 来缩小三点 diff（这不是 recipe 失败，不得规避）。
- 不把 JC6 误报当作 recipe 失败证据。

## 验证
- `git show-ref | grep 'origin/main'` → origin/main = upstream/main = 官方 OID（= HEAD）。
- `git diff origin/main...HEAD --name-status | wc -l` = 0（修复后三点 diff 空）。

## Source
- 证据（设备）：`progress.json jc6_fixes`（round-2/round-4 两条修复记录）、`worktree/ci/scripts/junk_check.sh`（line 35-44 incremental/full 判定、line 174-192 JC6 跳过单软件检查）、`git show-ref`
- 事件：dejagnu/1.6.3 CI rounds（round-2 / round-4 修复）
