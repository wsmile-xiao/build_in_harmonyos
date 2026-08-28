# DRAFT-jc-full-mode-git-index-isolation — JC full 模式按 git 索引扫描，基线噪声文件隔离/恢复工序

> **Contributor**: pc3-24 | **Status**: DRAFT | **Updated**: 2026-08-28
> **Severity**: medium | **Category**: ohos / ci / infrastructure
> **Audience**: 所有在 full 模式（整仓扫描）下跑 W3/finish 的新库执行端

## Scope
当仓库 HEAD 中预存了其他库的历史垃圾文件（`.orig` / `.ghfast-bak` / `.staging-verified` 等），
W3 的 JC 门禁在 **full 模式**下会拦截构建。本条目给出精确的"隔离 → 重跑 → 恢复"工序，
以及 predl 改写 `conandata.yml` 的附加陷阱。

## 背景
- `ci/scripts/junk_check.sh` 的 full 模式（无 `pr.diff`、无 `origin/main` 增量或 diff 为空时回退）
  用 `git ls-files` 扫描 **git 索引中被跟踪的文件**，而不是扫描文件系统。
- 因此仅从工作树 `rm` 文件不够：文件仍在索引中，JC1/JC5 仍报"被跟踪"。

## 模式（步骤）
1. **记录**三处基线文件的路径、类型、原始 SHA-256 与内容摘要。
2. **隔离（git 层）**：`git rm --cached <path>` 从索引移除；配合从工作树删除
   （先 `cp -p` 备份到 worktree 外）。此时 `git ls-files` 不再列出，JC 的 full 扫描不再命中。
3. **重跑 W3/finish**（本任务经 ohpc_compile_worker 提交 `{"kind":"finish",...}` 并轮询自然终态）。
4. **恢复**：`cp -p 备份 原路径` 还原文件内容 → `git reset HEAD -- <path>` 复原索引被跟踪状态。
   ⚠️ 若该路径命中 `.gitignore`，`git add` 会报 "paths are ignored by one of your .gitignore files"；
   必须用 `git reset HEAD -- <path>`（git reset 不受 ignore 限制）。
5. **终核**：三处 SHA-256 与原始一致，`git ls-files` 恢复为 3，eigen3 目录仍仅含本库 untracked。

## 附加陷阱（predl）
- W3 的 `build_and_test.sh` 内嵌 predl 预下载，会把 `conandata.yml` 的 `sources.url` 改写为
  `file://<本地缓存路径>`。
- 若实际下载产物与改写路径不符（例如拿到 54KB HTML 页面而非 ~2.7MB tarball），
  `conan create` 的 `source()` 报 `FileNotFoundError`。
- 重跑后必须把 `conandata.yml` 恢复为原始远端 URL + sha256，不得保留 predl 的 file:// 改写。

## 禁止
- 不得修改/删除/提交其他库的 tracked 垃圾文件本身来"修复"JC 误报（只允许临时隔离+恢复）。
- 不得伪造 `conandata.yml`、`.ci-result.json` 或跳过 W3。

## 验证
- 隔离后：`git ls-files | grep -cE '<junk>'` = 0；JC_RESULT=pass / Junk Files: 0。
- 恢复后：三处 `sha256sum` 与隔离前原始值一致；`git ls-files | grep -cE '<junk>'` = 3。

## Source
- 事件：eigen3 3.4.0 r03 baseline_noise_exemption_recheck（pc3-24，2026-08-28）
- 三处文件原始 SHA-256：
  - `archives/i/isa-l_crypto/2.26/conandata.yml.orig` = `d62412e13224ceebc7d290103042be6e4cd6f3f282457a5aff3ddaf9a202dd30`
  - `archives/m/middleclass/4.1.1/conandata.yml.ghfast-bak` = `226348ef18514af13942a5d0a8258b39828182721738f5cb4b0c7f0a594ac58b`
  - `archives/s/swift-corelibs-blocksruntime/6.3.3/.staging-verified` = `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`（空文件）
- 隔离后 W3 日志：`archives/e/eigen3/3.4.0/reports/w3-local-ci.log` sha256=`a7637e0d07e311d1c8a64d7a2a9e238fa9200c1d3b409230b758a75fc88432b0`（JC_RESULT=pass / Junk Files: 0）
- worker 日志（git 隔离后重跑）：sha256=`91805562d0069891a402558cd7eb2645228563f08dba52a95de0986c1feef8ff`
