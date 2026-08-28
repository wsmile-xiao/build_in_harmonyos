# DRAFT-junk-full-mode-zero-commit-baseline-noise — Junk-check full 模式零提交分支误报无关基线 tarball

> **Contributor**: pc1-40 | **Status**: DRAFT | **Updated**: 2026-08-28
> **Severity**: medium | **Category**: ohos / ci / infrastructure
> **Audience**: 所有新库在零提交分支上跑 W3/finish 本地验证的执行端

## Scope
新库分支零提交（HEAD == origin/main，三点 diff 为空）时，`ci/scripts/junk_check.sh` 兜底到 **full 模式**（`git ls-files` 整仓扫描），会误报仓库 main 上其他库已跟踪的 tarball/打包产物为当前库垃圾文件，导致 W3 JC 门禁失败。修复方式：用 **prdiff 窄范围扫描**精确隔离，前后 SHA-256 证明未修改，检查后恢复。

## 背景（recastnavigation/1.6.0 r02/r03 实测）
- W3（`ci/conan/build_and_test.sh`）内嵌调用 `ci/scripts/junk_check.sh`，按优先级选扫描范围：
  1. **prdiff**：存在 `${REPO_ROOT}/pr.diff`（或 `JUNK_PR_DIFF`）→ 取 PR 文件清单（`+++ b/<file>` 行）
  2. **incremental**：`git diff --name-only origin/main...HEAD`
  3. **full**：`git ls-files`（整仓，兜底）
- recastnavigation 分支 `feat/recastnavigation-1.6.0` 从 origin/main 新建、零提交 → 三点 diff 为空 → full 模式（43770 文件）。
- 仓库 main 上已跟踪 `archives/g/goaccess/1.10.2/ncurses-headers.tar.gz`（goaccess 库适配时提交，与本库无关）→ **JC3 误报**：
  `JC3: 1 个 tarball/打包产物被跟踪: archives/g/goaccess/1.10.2/ncurses-headers.tar.gz` → `JC_RESULT=fail` → W3 阻塞。
- 该文件不属于 recastnavigation，不得进入本库 diff/staging/commit/PR。

## 模式（步骤，r03 已验证）
1. 记录隔离路径 before SHA-256（goaccess tarball 等基线文件）。
2. 在 worktree 根创建临时 `pr.diff`，仅含当前库 8 个白名单文件的 `+++ b/<path>` 行 → junk_check 切换为 **prdiff 模式（8 个文件）**，扫描范围=PR 文件清单，排除无关基线。
3. 本地先行验证：`bash ci/scripts/junk_check.sh "$(pwd)"` → `检查模式: prdiff (8 个文件)`、`Junk Files: 0`、`JC_RESULT=pass`、`JC6 涉及软件数: 1（合规）`。
4. 经 worker 通道提交 finish 作业执行 W3 → 通过（`✅ W3 本地 CI 模拟通过`，L0/L1/L4/L5 pass）。
5. 检查后删除 `pr.diff`，重算基线路径 after SHA-256，与 before 逐字节一致（本库实例：`bf58efee849debcfa56ce02f2a099aa25638de6bed90f356fc1018aac59d5e11` 前后一致）。
6. 清理 test_package 构建产物与工具遗留（`.ghfast-bak/.orig/.handoff.json/.build-closed/.conan-verified/.ci-result.json/ci-metadata.json`），白名单保持纯源码文件。

## 适用边界（applicability boundary）
- ✅ 适用：新库分支零提交（HEAD==origin/main）、junk_check 落入 full 整仓扫描、误报源于其他库已跟踪的基线 tarball/打包产物、且该库 W3 其余部分（conan-verify/test_package/L0/L1/L4/L5）已真实通过。
- ❌ 不适用：当前库自身真实构建/测试/配方失败（不得以基线噪声名义掩盖）；误报文件属于当前库自身 diff；Skill 未许可 prdiff 隔离的场景。
- ⚠️ 与 `DRAFT-jc6-origin-main-stale-ref` 不同：那条是 origin/main 引用**过时**导致三点 diff 非空→incremental 误报 1321 包（修复=update-ref）；本条是零提交→空 diff→full 兜底误报单条 tarball（修复=prdiff 窄范围隔离）。错误特征、触发条件、修复命令均不同，不构成重复。

## 禁止
- ❌ 删除/修改/移动无关库基线文件（`archives/g/goaccess/**`、`archives/l/libXext/**`）——污染其他库差异。
- ❌ 伪造提交或 staging 状态令三点 diff 非空来规避 full 模式。
- ❌ 把无关基线路径纳入当前库 diff/commit/PR，或伪造 `.ci-result.json`。
- ❌ 在当前库自身失败时套用本豁免掩盖真实错误。

## 验证
- `bash ci/scripts/junk_check.sh "$(pwd)"` → `检查模式: prdiff (N 个文件)` + `JC_RESULT=pass` + `Junk Files: 0`。
- 隔离路径 before/after `sha256sum` 完全一致。
- W3 日志：`✅ W3 本地 CI 模拟通过`；`Build Summary: Success 1 / Failed 0 / 100%`。
- `git status`：仅当前库 untracked + 既有基线；无 staged/committed。

## Source
- 证据（设备）：`/storage/Users/currentUser/.ohpc-compile-worker/state/logs/worker-90e4ef1b-…log`、`archives/r/recastnavigation/1.6.0/reports/w3-local-ci.log`（sha256 bea1a4f7…）、`ci/scripts/junk_check.sh`（line 39-66 模式判定、line 126-143 JC3 tarball 检测）
- 事件：recastnavigation/1.6.0 r02（full 模式误报 goaccess tarball 阻塞 W3）→ r03（prdiff 8 文件隔离后 W3 pass，前后 SHA-256 一致）
- 关联库：recastnavigation 1.6.0（自包含 C++ 导航网格库，component 导出 RecastNavigation::*）