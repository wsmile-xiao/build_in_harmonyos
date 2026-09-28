# DRAFT-liblzf-3.6.1-r38-version-bump-commandsjson-and-local-ci-merge-base

## 基本信息
- **严重度**: 2
- **类别**: ci, quality-gate, commands.json, R38, R40, branch-name, package-name, local-ci-parity, merge-base
- **来源 PR**: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/pull/12428

## 错误特征
```
L0k: commands.json missing version 3.6.1 (R38)|
递增版本号时须同步在 commands.json 的 versions 中补 <version>|
L0n: branch name mismatch (R40) — 分支完全不包含 包名-版本号|
JC6: 本 PR 涉及 N 个软件包，违反 W2 单软件原子性（本地复跑时）
```

## 根因分析
liblzf 3.6.1 是 3.6 的迭代版本，PR 分支 feat/libblzf-3.6.1 为任务指定分支名
（**任务要求包名即 libblzf，并非 typo**——上游真名 liblzf，任务名 libblzf，
两者不一致时以任务/分支名为准）。归档曾用上游真名 liblzf 建目录
archives/l/liblzf/3.6.1/，软件级 commands.json 的 versions 只登记了 "3.6"，
L0k 报 commands_json_r38；叠加 pkg_name（按目录解析）=liblzf 与分支名
libblzf-3.6.1 不匹配触发 branch_name_r40。两处都在 L0 gate 拦截
（L1/L2/L4/L5 全部 skip blocked_by_L0），无需用户提供完整日志即可从失败
评论的 L0 段落直接定位。

核心教训（v12.20 增补）：**分支名 ≠ typo 时不要改分支**——任务指定的包名
与上游真名不一致（libblzf vs liblzf）是任务命名口径，正确修法是**把归档
目录/包名/commands.json/manifest 全部对齐分支名**（包名 libblzf，目录
archives/l/libblzf/3.6.1），上游源码 URL 仍指向官方源（R39：URL 必须是
官方源，包名可以不同于上游名）。改分支名需重建分支与 PR，代价远高于
改包名。

次要教训：本地复跑同一 PR 时 JC6 误报 122 个软件包 —— junk_check.sh 的
incremental 模式用 `git diff origin/main...HEAD` 取变更文件，本地 origin/main
落后远端（merge-base 过旧）会把历史上已合并的包全算进本 PR。fetch 远端 main
后 diff 只剩 liblzf，JC6 恢复合规。本地通过与 PR CI 不一致的常见根因之一就是
diff 基线陈旧，先 `git fetch origin main` 再复跑。

## 推荐方案
**方法**: bump-version-sync-commandsjson-versions-and-align-package-name-with-branch

**说明**:
1. R38 双登记：软件级 `archives/<letter>/<pkg>/commands.json` 的 versions
   必须为每个新增版本补 `{ "ref": "<pkg>/<ver>", "binary": false }` 条目
   （tool 类型；库类型无 commands.json 不涉及）。
2. R40 命名：分支名必须以 `包名-版本号` 结尾（feat/|fix/ 前缀后
   fullmatch/包含 `libblzf-3.6.1`）。**分支名是任务指定的，不可随意改名**；
   任务名与上游真名不一致时（libblzf vs liblzf），把归档目录、conanfile
   name、commands.json name、manifest software 全部对齐分支名/任务名，
   上游 conandata URL 保持官方源不变。
3. 本地复跑 parity：worktree 中先 `git fetch origin main` 保证三点 diff
   merge-base 新鲜，再
   `CI_PACKAGES="archives/l/libblzf/3.6.1" CI_BRANCH="feat/libblzf-3.6.1" zsh ci/conan/build_and_test.sh`。

## 验证/命令
```
CI_PACKAGES="archives/l/libblzf/3.6.1" CI_BRANCH="feat/libblzf-3.6.1" zsh ci/conan/build_and_test.sh
# 期望 L0_RESULT=pass（L0n: branch 'feat/libblzf-3.6.1' matches 'libblzf-3.6.1' exactly）且 Build Summary Success: 1
```

## 关键词
liblzf, libblzf, R38, commands.json, versions, R40, branch_name, L0k, L0n,
包名对齐分支名, 任务名≠上游名, 本地CI复现, merge-base, origin/main 落后,
JC6 误报, 单软件原子性, 版本迭代, 3.6.1

---
*2026-09-25 由构建 #60230/#60624/#60644 失败复盘生成并修订（包名对齐分支名方案）*
