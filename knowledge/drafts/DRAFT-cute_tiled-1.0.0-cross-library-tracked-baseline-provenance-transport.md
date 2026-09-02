# DRAFT-cute_tiled-1.0.0-cross-library-tracked-baseline-provenance-transport

> 草稿（Path B 知识库扩展候选），由 cute_tiled 1.0.0 跨库 tracked 基线证据运输协议审计产生。
> 本文与同名 `.kv` 配对，逐字段一致。仅为本地知识草稿，不代表任何 PR/Issue/commit/push/CI/review/merge/score 或远端客户端修复已成功。

## topic

跨库 tracked 基线变更的运输安全证据协议：为 out-of-scope 跨库 tracked 变更保留精确路径身份与前后不变性证据，使审计证据可运输、可复核、不被误判为当前库污染。

## error_signature

当前库环境的原子性证据把 pre-existing 跨库 tracked 变更降为"变更计数 N"，却不给精确路径，也不给各路径变更前后的工作树内容哈希与 `git diff --binary` 哈希，导致越界基线的身份与不变性在运输后丢失、不可追溯。

## root_cause

out-of-scope 的 tracked 跨库（如 libXext）工作树变更在 cute_tiled worktree 创建前就已存在；当审计证据省略身份（精确路径）与不变性（前后内容 + 二进制 diff 哈希）时，这类变更可能被误认为当前库污染，造成 PR 范围判定错误或无关清理要求。

## durable_solution

1. 枚举精确基线路径（如 `archives/l/libXext/README.md`、`archives/l/libXext/manifest.yaml`），声明其不属于当前库文件白名单。
2. 交付（commit/push/PR 或任何远端动作）前后，对每个基线路径记录并对比两对值并要求完全相等：
   - 该路径工作树 SHA-256（`sha256sum <path>`）；
   - 该路径 `git diff --binary -- <path>` 输出的 SHA-256。
3. 分别证明 `archives/c/cute_tiled/**` 无 staged/unstaged 变更，且 git index 为空（`git diff --cached --name-only` 计数为 0）。
4. 绝不对跨库基线文件执行 clean/restore/stage。

## impact

若证据仅含计数而无身份/不变性，跨库基线在运输后无法复核，退化为不可追溯的"当前库异常"断言；正确协议让任何后续审计都能核对基线零修改并复核范围判定。

## recovery_condition

若任一通用客户端或 preflight 对"任何 unstaged 变更"一律拒绝（无论是否在当前库范围），这是共享客户端/preflight 的限制；应在不修改跨库基线文件的前提下修复该共享客户端。远端 Path B 交付（commit/push/PR/Issue）延期至后续授权任务，使用分析端准备的权威 Issue 模板与官方 PR 模板。

## evidence_references

- 既有不可变提交 `4d4ea63bb75f8d161eed37ba72cf3d68bdbeb687`（分支 `feat/cute_tiled-1.0.0`，15 文件精确 whitelist）。
- libXext 基线 prestate/poststate 哈希证据（工作树 + `git diff --binary`，前后相等）。
- 当前库可爱交付的原子性审计记录（index 空、cute_tiled/** 无变更）。

## status

draft_pending_review
