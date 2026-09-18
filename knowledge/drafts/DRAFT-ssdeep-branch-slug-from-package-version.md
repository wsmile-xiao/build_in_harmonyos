# DRAFT: 分支名须以 Conan 包版本号结尾（R40/L0n）——误用上游 tag 名触发门禁及修复闭环

> 草稿条目（与 `DRAFT-ssdeep-branch-slug-from-package-version.kv` 同 stem 配套）。
> 状态：DRAFT — 待人工/AI 审核提升为 E-条目。

## 问题现象（ssdeep 2.8 R02 实测）

远端 CI（build #49031, conan-build-test）L0 门禁失败：

```
L0n R40 分支名校验失败（branch_name_r40）：
分支 'feat/ssdeep-release-2.8'（去前缀后 'ssdeep-release-2.8'）
不包含包名-版本号 'ssdeep-2.8'；分支必须以 包名-版本号 结尾。exit code 1
```

## 根因

R01 任务版本 slug 使用上游 git tag 名（`release-2.8`）直接生成分支 `feat/ssdeep-release-2.8`，
而 Conan 包版本号为 `2.8`（`archives/s/ssdeep/2.8/`、manifest `version: "2.8"`、
commands.json `versions.2.8` 三处一致）。分支去前缀后不含"包名-版本号"，触发 R40/L0n 校验失败。
分支 slug 的唯一权威来源是 **Conan 包版本号（版本目录 slug）**，不是上游 tag 字符串。

## 方案（修复闭环，R02 实测）

```bash
# 1. 分支改名（同一 HEAD，禁止强制推送、变基或合入）
git branch -m feat/ssdeep-2.8
# 2. push 新分支（同 HEAD 新 ref）
git push origin feat/ssdeep-2.8
# 3. PR 源分支更新：PATCH pulls API 一般不支持改 source_branch（仅 title/body/state）
#    不支持时关闭旧 PR（注明分支更名原因），在新分支创建同标题正文新 PR
gitcode_pr.py update-pr --repo OpenHarmonyPCDeveloper/build_in_harmonyos --number 10456 --state closed
gitcode_pr.py create-pr --repo OpenHarmonyPCDeveloper/build_in_harmonyos \
    --source feat/ssdeep-2.8 --target main \
    --title "<同标题>" --description "<同正文>" --no-preflight
# 4. 触发一次 /rebuild 复验 R40
gitcode_pr.py trigger-ci --repo OpenHarmonyPCDeveloper/build_in_harmonyos --number <new>
```

**预防**：新库首次建分支时直接以 包名-版本号（版本目录 slug）命名，不要用上游 tag 字符串。
与 slug 家族一致：目录 / 配方 version / MANIFEST / commands.json / 分支 五处使用同一 slug。

## 验证（ssdeep 2.8 R02）

- 本地：`git branch -m` 后 worktree 唯一性 1（`git worktree list --porcelain`），
  HEAD 860cd4a573 不变；push exit=0，远端 `refs/heads/feat/ssdeep-2.8 = 860cd4a573`；
- PR：#10456 关闭（注明原因），#10508 同标题正文重建，/rebuild note_id 190099311；
- 远端 R40 复验：以 CI 实际结果为准（本回合已触发，结果见回传）。

## 适用边界 / 反例

| 场景 | 适用性 |
|------|--------|
| 上游 tag 名 ≠ Conan 版本 slug（release-/v- 前缀、日期、额外标识） | ✅ 分支必须以版本号命名；本文修复链适用 |
| tag 名 == 版本号（如 v2.8 → 需 strip 前缀，2.8） | ✅ 分支名取剥离后版本号 |
| 分支尚未推送 | ⏭ 直接改名为对即可，无需 PR 重建 |
| 版本 slug 已小写/规范（大写 tag、单字符版本） | ⚠️ 走 slug 小写化家族（E416/E999/hfsm2/E563），非本条场景 |
| 分支名与版本号一致但 CI 红 | ❌ 非 R40 问题，按实际门禁诊断 |

## 关系

- similar_to: E470（上游 version 与 tag 不一致，tag 为 provenance 源）、E416（conan slug）、
  E563-draft-A465（单字符版本/L0n 分支门禁）、E999-draft-35E4（大写版本 slug 与分支三处一致）、
  DRAFT-hfsm2-beta73-uppercase-tag-version-slug（大写 tag→slug 小写）
- 差异：本条目首次单列"分支误用上游 tag 名（release- 前缀）而非 Conan 版本号 → R40 门禁
  + branch -m → PR 关闭重建 → /rebuild"完整闭环；预防规则（新库直接以版本号命名分支）可跨库复用。
- 未动 DRAFT-ssdeep-oldautotools-m4-config-guess-chain（R01 草稿保持原样）。

## 相关知识来源

- 三方库：ssdeep 2.8（archives/s/ssdeep/2.8，PR #10508，R02）
- 门禁定义：SKILL.md §1.3 R40 / CI L0n