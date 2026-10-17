# Knowledge Candidate Ledger — brieflz 1.3.0

**日期**: 2026-09-19
**任务**: brieflz-1.3.0-r01-pc1-35（知识库扩展候选评估）
**执行端**: pc1-35 @ build_in_harmonyos worktree `feat/brieflz-1.3.0`

## 一、知识候选台账（逐项非噪声候选）

### 候选 1: CMake 4.x 拒绝 cmake_minimum_required(<3.5) — Conan recipe 内必须走 configure 命令行参数

- **真实错误**: `CMake Error at CMakeLists.txt:1 (cmake_minimum_required): Compatibility with CMake < 3.5 has been removed`；G2 conan create 首次配置失败（logs: `reports/conan-create.log`，退出码 1）
- **根因**: brieflz 上游 CMakeLists.txt 声明 `cmake_minimum_required(VERSION 2.8.11)`；本机/CI 使用 CMake 4.1.2，移除了 <3.5 兼容策略。修复变量 `CMAKE_POLICY_VERSION_MINIMUM` 必须在 `cmake_minimum_required()` 执行前生效——Conan `CMakeToolchain.tc.variables` 写入 conan_toolchain.cmake（在项目 CMakeLists 的 cmake_minimum_required 之后才被 include），**无效**（首次用 tc.variables 实测 G2 仍失败）；`cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})` 走 `-D` 命令行参数，在任何 CMakeLists 解析前生效，**有效**
- **修复**: conanfile.py `build()` 中 `cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})`；本地直编同样加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`
- **验证**: conan-verify G2 conan create 通过（rc=0）；本地 cmake+make+ctest 通过（rc=0）
- **适用范围**: 所有 cmake_minimum_required(<3.5) 的老项目在 CMake ≥4.x 工具链（OHOS SDK 当前 4.1.2 必然触发）下的 Conan 配方与直编；cross-library 可复用
- **四范围查重**: 正式知识 **E187（add-cmake-flag，命中）**、E103（bump-cmake-minimum-version，部分）；图谱 index 命中；草稿 **DRAFT-E321-cmake4-policy-version-minimum.kv（命中，含“切勿用 tc.variables、须 cache_variables/-D”同一结论）**；正式知识 doc/E187.md 已有 `cmake -DCMAKE_POLICY_VERSION_MINIMUM=3.5 ..` 命令

### 候选 2: W3/JC1 全仓扫描命中其他库已跟踪基线空文件 — 临时索引隔离复验

- **真实错误**: finish [5/10] W3 本地 CI 模拟 `JC_RESULT=fail`（Junk Files: 2）：`archives/c/cloog/0.21.1/.build-closed`、`.staging-verified`
- **根因**: 当前库分支零提交（HEAD==origin/main 基线），junk_check 落入 **full 模式**（`git ls-files` 整仓已跟踪文件），命中 origin/main 上游遗留的其他库（cloog）运行时状态标记；两文件在 main/HEAD 均为空 blob `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391`（SHA-256 `e3b0c442…855`），非本 worktree 引入；`git status` 对该路径本为干净
- **修复**: 记录路径+隔离前 SHA-256 → `git rm --cached` 临时摘除索引（工作树文件保留、内容零修改）→ 重跑 finish/W3（JC/L0-L5 全 pass）→ `git add` 恢复索引并核对 SHA-256/blob/Git 状态逐项一致；未修改/未提交/未 PR 该基线文件
- **验证**: 隔离后 `git ls-files` 两文件计数=0、JC_RESULT=pass；恢复后 SHA-256 仍 `e3b0c442…855`、HEAD blob 一致、git status 干净、当前库 diff/staged/PR 不含该路径
- **适用范围**: 共享 build_in_harmonyos 仓库中新库分支零提交时 W3/finish 全仓扫描命中其他库已跟踪隐藏标记/tarball 的基线噪声；cross-library 可复用
- **四范围查重**: 正式知识 **E291（repository_baseline_blocked，相关命中）**；图谱命中；草稿 **DRAFT-dr_mp3-0.7.2-baseline-noise-isolation（.md+.kv，同一“git rm --cached 索引隔离+重跑+恢复审计”方案，命中）**、**DRAFT-jc-full-scan-baseline-noise-exemption（同因 full 模式误伤，命中）**

### 噪声项（不入账）
- `blz_depack_safe` 需精确 depacked_size（传大一字节即 BLZ_ERROR）：库特有 API 语义，非跨库可复用知识 → 噪声，仅在 test_package/test.c 注释与 test-report 中记录

## 二、七轴查重（候选 1 / 候选 2）

| 轴 | 候选 1（CMake 4 策略） | 候选 2（JC 基线隔离） |
|---|---|---|
| exact_duplicate | false（DRAFT-E321 为 .kv 草稿未提升，正式 E187 仅给命令不给 Conan 注入点细节） | false（既有草稿场景为 goaccess tarball + scudo-malloc 标记，本次为 cloog 空文件，路径不同） |
| causal_duplicate | true（同一根因：CMake 4.x 移除 <3.5 兼容，触发点一致） | true（同一根因：零提交分支 junk_check full 模式扫整仓命中其他库基线） |
| trigger_overlap | true（错误签名同一正则族） | true（JC_RESULT=fail / blocked_by_JC 同一签名） |
| solution_overlap | true（同一方案：-D 命令行注入 CMAKE_POLICY_VERSION_MINIMUM；DRAFT-E321 已含“勿用 tc.variables”） | true（同一方案：git rm --cached 临时索引隔离 + 恢复审计） |
| combination_novelty | false（无新组合；本轮为 DRAFT-E321 结论的第三次同向实证） | false（dr_mp3 草稿已给出完整操作步骤，本轮为同一流程） |
| boundary_novelty | false（无新边界；适用边界=老 CMakeLists+CMake≥4，已有草稿表述） | false（适用边界=零提交新库+full 扫描+其他库跟踪基线，dr_mp3 草稿已表述） |
| test_migration_novelty | false（与测试迁移无关） | false（与测试迁移无关） |

**关系字段**：
- 候选 1: `similar_to` E187/E103；`caused_by` CMake 4.x 兼容策略移除；`prerequisite_of` 无；`conflicts_with` 无
- 候选 2: `similar_to` E291、DRAFT-dr_mp3、DRAFT-jc-full-scan；`caused_by` junk_check full 模式；`prerequisite_of` 无；`conflicts_with` 无

## 三、路径决定

**`reuse_existing`** — 两项候选均被既有正式知识（E187/E103/E291）与既有草稿（DRAFT-E321、DRAFT-dr_mp3-0.7.2-baseline-noise-isolation、DRAFT-jc-full-scan-baseline-noise-exemption）完整覆盖；causal/solution/trigger 三轴重叠，无新增差异可跨库复用 → **路径 A（常规基础适配，复用既有知识），不新建草稿**；本任务按任务头 `task_type: 知识库扩展`、`initial_pr_prefix: 【知识库扩展】` 交付（无 new_draft 不建 .md/.kv 配对）。已按“不能只查标题/库名/关键词”完成全维度查重并附证据。

**决定依据**（knowledge-reuse-governance）: 完整重复 → 复用原条目并走路径 A；本轮未证明新增知识价值，路径 B 不成立（如实回报）。
