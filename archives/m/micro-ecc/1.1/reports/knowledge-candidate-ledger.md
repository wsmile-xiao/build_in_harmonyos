# 知识候选台账 — micro-ecc 1.1（R01，pc4-12）

> 任务路径判定：`task_type: 知识库扩展`（B）。每项候选记录真实错误、根因、修复、
> 验证、适用范围与四范围查重（正式知识 knowledge/graph/E*.kv、doc/、草稿 knowledge/drafts/、图谱 index.tsv）。

## 候选清单

### C1: W3/JC5 全量模式命中「gitignore 但仍被跟踪」的其他库基线文件（.ci-trigger）

- **真实错误**：`finish` step [5/10] W3 本地 CI 被 JC5 拦截：`archives/u/util-linux-login/2.42.2/.ci-trigger` 为未登记 archives 隐藏文件，JC_RESULT=fail → L0 fail → blocked_by_JC。
- **根因**：junk_check.sh 在 full 模式（零提交新库分支，`git diff origin/main...HEAD` 为空 → 回退 `git ls-files` 整仓扫描）按 **git index** 扫描 `archives/.*/\.[^/]+$` 隐藏文件。`.ci-trigger` 已被主仓 main 提交跟踪（util-linux-login 2.42.2 PR 761df452e5）且 `.gitignore:210` 有 `**/.ci-trigger` —— **gitignore 只影响未跟踪文件的 add，不影响已跟踪文件出现在 git ls-files**，故仅移出工作树文件无法消除命中，必须从 index 临时移除。
- **修复**：`git rm --cached <路径>`（人类可读证据：content 为空文件，sha256 e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855）→ 复跑完整 `finish`（W3 通过，JC 不再命中）→ 恢复用 `git checkout HEAD -- <路径>`（gitignore 下 `git add` 会被拒，checkout 直接恢复 index+worktree）→ 核验恢复后 SHA-256 == 隔离前 SHA-256、ls-files 恢复跟踪、git status 无该路径。
- **验证**：第一轮（仅移出工作树）仍命中；第二轮（残留 .isolated 副本）仍命中；第三轮（`git rm --cached` + 复跑）W3 通过、finish 走到知识整理阶段；恢复后 SHA-256 e3b0c442… 一致（`git status` 无该路径变更）。
- **适用范围**：所有在共享 build_in_harmonyos 仓库零提交新库分支上执行 W3/finish，且 main 上存在其他库遗留「gitignore 但仍被跟踪」隐藏标记（如 **/.ci-trigger）的执行端。
- **四范围查重**：
  - 正式知识：E291（repository_baseline_blocked，graph validate 基线阻塞，非同一问题）；无正式条目覆盖「JC5 full 模式 git-index 隔离」。
  - 图谱：index.tsv 无 `jc5|junk_check|git rm --cached|ci-trigger` 顶点。
  - 草稿：DRAFT-dr_mp3-0.7.2-baseline-noise-isolation.kv 覆盖同根因（JC5 full 模式 + git ls-files + 隔离复验），但其 restore 用 `git add -f`；本候选新增差异：**gitignore-but-tracked 文件（.ci-trigger）必须用 `git checkout HEAD --` 恢复，`git add` 被 ignore 拦截**，且该文件同时命中 `.gitignore` 规则与 `git ls-files` —— 隔离/恢复命令路径完全不同。DRAFT-cute_tiled-1.0.0-cross-library-tracked-baseline-provenance-transport 覆盖跨库 tracked 基线证据运输，与本候选（JC5 门禁隔离机制）互补。

### C2: GitHub 直连超时 → 使用官方 codeload 端点下载同一官方 tarball

- **真实错误**：`curl https://github.com/kmackay/micro-ecc/...` 连接超时；`api.github.com` 限流。
- **根因**：网络环境对 github.com 主域直连不稳定（E017 已知模式）。
- **修复**：改用官方 codeload.github.com 下载端点获取同一 tag tarball，SHA-256 与 conan 源 URL（github.com 官方 URL，R39 保持）核验一致。
- **验证**：tarball sha256 0e39fba5… 与 conan create 实际下载解压产物一致；conan-verify G2 通过。
- **适用范围**：GitHub 主域直连超时的源码获取场景。
- **四范围查重**：E017（GitHub 超时→ghfast 镜像）trigger_overlap；E406（sha256 多路径交叉验证，含 codeload）solution_overlap；DRAFT-dr_wav-0.13.17-codeload-archive-mime（codeload mime）trigger_overlap。**既有条目已覆盖，无新增差异 → 复用 E017/E406，不建草稿**。

### C3: test_package 引用库内部宏编译失败 → 改用编译器宏

- **真实错误**：`test_ohos.c:24:13: error: use of undeclared identifier 'uECC_PLATFORM'`。
- **根因**：`uECC_PLATFORM` 是 types.h（库内部头）宏，uECC.h 未导出；消费者视角不可用。
- **修复**：断言编译器宏 `__aarch64__`（与 types.h 平台推导一致）。
- **验证**：conan create ctest 2/2 通过。
- **适用范围**：库特定（micro-ecc），非跨库通用知识 → **not knowledge（库级 notes 已记录，不计草稿）**。

## 七轴查重（仅对候选 C1，走 path B 判定）

| 轴 | 结论 |
|----|------|
| exact_duplicate | 否 — dr_mp3 草稿对象是 JC3(tarball)+JC5 双标记且 restore 命令不同；本候选为 gitignore-but-tracked 单文件（.ci-trigger） |
| causal_duplicate | 部分 — 根因同族（full 模式 git ls-files 扫描其他库基线），但 gitignore-but-tracked 文件的隔离/恢复路径不同 |
| trigger_overlap | 高 — 同为 JC5 full 模式；但本候选触发文件同时命中 `.gitignore`（**/.ci-trigger）与已跟踪状态，是 dr_mp3 未覆盖的形态 |
| solution_overlap | 低-中 — 隔离命令 git rm --cached 相同；恢复命令不同（git add -f vs git checkout HEAD --） |
| combination_novelty | 有 — gitignore 规则与 git ls-files 已跟踪共存时的门禁行为 + 恢复命令约束（git add 被拒 → 必须 checkout HEAD）为新组合 |
| boundary_novelty | 有 — 明确边界：gitignore 不豁免已跟踪文件的 JC5 扫描；`.ci-trigger`/`**/.ci-trigger` 类标记即使 gitignore 仍会被隔离复验流程命中 |
| test_migration_novelty | 无 — 不涉及测试迁移 |

## 路径决定

- **C1**：部分覆盖（dr_mp3 草稿已存在），但新增差异（gitignore-but-tracked 基线的 checkout HEAD 恢复）已由本轮真实日志验证且可跨库复用 → **new_draft（path B）**，建立同 stem 的 .md/.kv 草稿。
- **C2**：既有条目覆盖 → reuse_existing（E017/E406）。
- **C3**：库特定 → path_a_no_knowledge（notes 记录即可）。
- 最终：**path_b_new_draft**（C1 唯一建草稿），与 micro-ecc 归档同 PR 交付。