# DRAFT-minicoro-0.1.3-r40-branch-naming-vslg — CI R40 分支命名硬门禁：版本 slug 不得带上游 v 前缀

> **Contributor**: pc1-49 | **Status**: DRAFT | **Updated**: 2026-09-18
> **Severity**: high | **Category**: ci / conan / branch / naming / versioning
> **Audience**: 适配任何上游 tag 带 `v` 前缀（v0.1.3 类）而注册表版本 slug 不带（0.1.3）的库；以及分支改名后需要处理 PR head 跟随的执行端

## 问题签名与触发条件

真实 CI 失败（minicoro/0.1.3 R01 交付后 /rebuild）：

```text
[step] L0n: Checking branch name matches package (R40)...
[error] L0n: branch name mismatch (R40) — 分支完全不包含 包名-版本号
       分支 'feat/minicoro-v0.1.3'（去前缀后 'minicoro-v0.1.3'）不包含 'minicoro-0.1.3'
[hint] 分支名必须以 包名-版本号 结尾，例如：minicoro-0.1.3 / feat/minicoro-0.1.3 / fix/minicoro-0.1.3
[fail] minicoro/0.1.3 — L0 quality gate failed: branch_name_r40
L0_RESULT=fail: gate failed: branch_name_r40
  Pass rate: 0.0% (0/1)
```

触发条件：
- 上游官方 tag 带 `v` 前缀（`v0.1.3`），注册表版本 slug 不带（`0.1.3`）
- 分支名误用上游 tag 原样（`feat/<lib>-v0.1.3`）
- CI L0n（R40）全量硬门禁：去前缀后必须与 `包名-版本slug` 逐字节相等

## 根因

CI L0n（R40）分支命名门禁（v12.10.2 起全量拦截）：分支名剥掉可选前缀
（feat/ fix/ 等）后必须精确等于 `包名-版本slug`，不允许额外后缀。注册表版本
slug 来自 `archives/<字母>/<库>/<版本>/` 目录名（如 `0.1.3`），而上游 tag 常带
`v` 前缀（`v0.1.3`）。R01 把 tag 误用为 slug 写入分支 → tag/slug 语义混淆被门禁拦截。

## 修复方案

**方法**: strip-upstream-v-prefix-in-branch-slug

1. 分支名使用**注册表版本 slug**而非上游 tag：
   `git branch -m feat/<lib>-v0.1.3 feat/<lib>-0.1.3`
2. 推送新分支：`git push -u origin feat/<lib>-0.1.3`
3. 本地复核 L0n 逻辑（去前缀+逐字节比较）PASS
4. PR head 切换若遇平台限制（v5 API 不接受 head/source_branch 字段、PUT 405、
   /api/v4 403 禁用、PR closed 且 can_reopen=false）：按任务已知恢复规则记录
   平台行为，不 force-push/rebase/merge，不关闭重建 PR，
   旧远端分支在确认 head 跟随前不删除

验证命令：

```bash
git branch --show-current            # feat/minicoro-0.1.3
BRANCH_NORM=$(echo "feat/minicoro-0.1.3" | tr '+' '-'); B="${BRANCH_NORM##*/}"
[ "$B" = "minicoro-0.1.3" ] && echo "L0n: PASS"
```

## 适用范围与边界

- 适用：tag 带 `v` 前缀而 slug 不带、tag 大小写与 slug 不一致（呼应 E999）等
  tag≠slug 场景的分支命名
- 反例/不适用：tag 与 slug 一致（如 `1.2.3` == `1.2.3`）时无需剥离；
  分支带额外后缀（`-ASDH`）是 L0n 后缀拦截的另一错误模式，方案不同
- 平台行为（PR head 跟随）：gitcode v5 API 无 head/source_branch 更新字段，
  PR head 由后端/人工在预检通过后统一推送更新（sipsak/asterisk-flite 先例同）

## 查重与关系

- 四范围：index.tsv / doc / graph 无 L0n/R40 分支命名条目；E999-draft-35E4
  （prover9 大写 tag→小写 slug）覆盖"分支名=slug"原则但未展开 v 前缀剥离边界
- 七轴：exact_duplicate=false, causal_duplicate=false, trigger_overlap=false,
  solution_overlap=true（部分：分支名=slug 原则与 E999 相同）,
  combination_novelty=true, boundary_novelty=true, test_migration_novelty=false
- 关系：similar_to=E999-draft-35E4、E416；caused_by=CI L0n/R40 分支门禁；
  prerequisite_of=无；conflicts_with=无
- 决定：**new_draft**（路径 B），.md/.kv 成对，随 minicoro 归档同 PR

## 来源

minicoro/0.1.3 R02（pc1-49, 2026-09-18）：R01 CI L0n branch_name_r40 失败 →
分支改名 feat/minicoro-0.1.3 + 推送 + PR head 切换平台限制记录