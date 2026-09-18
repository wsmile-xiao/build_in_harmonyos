# minicoro 0.1.3 知识候选台账（knowledge_candidate_ledger）

任务: minicoro-v0.1.3-r01-pc1-49 · 任务类型: 知识库扩展（路径 B 判定见文末）
查重范围: knowledge/doc/（正式 E###.md）、knowledge/graph/（E###.kv + index.tsv）、
knowledge/drafts/（草稿 .md/.kv）、knowledge/graph/index.tsv 四范围

## 候选 A：W3/JC full 模式整仓扫描命中其他库基线隐藏标记（cloog）
- 真实错误: `finish` W3 本地 CI 的 junk_check.sh 报 `Junk Files: 2`、
  `JC1: 2 个运行时状态文件被跟踪`、`JC5: 2 个 archives 下未登记的隐藏文件`，
  命中 `archives/c/cloog/0.21.1/.build-closed` 与 `archives/c/cloog/0.21.1/.staging-verified`，
  `blocked_by_JC` → L0 失败 → W3 阻塞（Pass rate 0.0% (0/1)）
- 根因: junk_check.sh full 模式（零提交新库分支 HEAD==origin/main，无 PR diff 可比较）用
  `git ls-files` 整仓扫描；cloog 适配 PR（906cc59ae7）把两个运行时标记文件提交进了 main，
  属其他库历史遗留基线噪声，与当前库无关
- 修复: 基线隔离复验——`git rm --cached` 精确移出索引（工作树保留、零内容修改）→ 重跑
  W3（build_and_test.sh pass 100%）→ `git add -f` 原样恢复 → 恢复前后 SHA-256 均为
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`（空文件）一致，
  git diff HEAD 为空、索引与 HEAD 一致，未修改/提交/带入 PR
- 验证: 隔离后 `zsh ci/conan/build_and_test.sh archives/m/minicoro/0.1.3` →
  `JC_RESULT=pass`、`L0_RESULT=pass`、Pass rate 100% (1/1)；恢复后 diff 干净
- 适用范围: 所有在共享 build_in_harmonyos 仓库执行 W3/finish 且分支零提交、命中其他库
  基线 junk 的执行端
- 四范围查重: **完全重复** — DRAFT-dr_mp3-0.7.2-baseline-noise-isolation、
  DRAFT-jc-full-scan-baseline-noise-exemption、DRAFT-jsoncons-1.9.0-test-count-and-baseline-noise、
  DRAFT-cute_tiled-1.0.0-cross-library-tracked-baseline-provenance-transport、
  DRAFT-kdbusaddons-baseline-noise-isolation 已覆盖同根因同方案（git rm --cached 隔离 +
  复跑 + git add -f 恢复 + SHA-256 审计）
- 七轴查重: exact_duplicate=true, causal_duplicate=true, trigger_overlap=true,
  solution_overlap=true（与既有草稿逐项一致）→ **reuse_existing**，不新建草稿；
  本库仅提供 cloog 新实例（文件路径不同，模式无新增）

## 候选 B：单头文件协程库在 OHOS aarch64 的实现后端自动选择与验证
- 真实错误: 无编译错误——适配问题在于**验证语义**：minicoro 是单头文件 C 库，消费者在
  一个翻译单元 `#define MINICORO_IMPL` 编译实现；aarch64-linux-ohos 下 minicoro.h 的
  `__aarch64__` 分支（L1081 附近）自动选择 MCO_USE_ASM 汇编后端，无需 ucontext/fibers，
  也无需任何源码补丁
- 根因: 上下文切换类单文件库（协程/协程后端）按架构宏选择汇编后端；若 OHOS 专项测试
  不验证后端选择，就无法证明 aarch64 汇编路径（而非回退路径）实际生效
- 修复: 新建 test_ohos_platform.c 鸿蒙专项测试——编译期断言 `MCO_USE_ASM` 被选中 +
  运行期验证嵌套协程、深度 C 调用链 yield、自定义分配器（malloc_cb/free_cb 签名
  `(size_t, void*)`/`(void*, void*)`）语义；15/15 断言通过
- 验证: OHOS Clang 15.0.4 编译零警告，运行输出 `OHOS impl: MCO_USE_ASM (aarch64
  assembly context switch)`、`minicoro OHOS platform test: 15 assertions passed`，
  RUN_EXIT=0；日志
  `/storage/Users/currentUser/tmp/ohlogs/ohos_test_run.log`（SHA-256
  `1ed8c4643e5d500a0d366bc3b448b579938de09bf95f02d38cb23e37416c992d`）
- 适用范围: 任何单头文件、含架构相关汇编/上下文切换后端的 C/C++ 库（minicoro 类协程库、
  boost.context 类、libco 类、ucontext 封装类）在 OHOS aarch64 的适配验证
- 四范围查重: **部分覆盖** — E257（header-only 无 CMake 库 no-op build() 满足 G1）、
  E321（martinmoene lite 系 header-only Conan 2.x 迁移）、E322（header-only cmake
  INTERFACE recipe）、E470（header-only recipe 综合）覆盖 header-only 配方的
  package_type=header-library / cpp_info.set_property / cmake_layout / test_package 结构；
  但**未覆盖**：①单文件 C 库 `#define XXX_IMPL` 单翻译单元消费模式；
  ②协程/上下文切换库按架构宏自动选汇编后端、OHOS aarch64 专项测试验证后端选择的方法
- 七轴查重: exact_duplicate=false, causal_duplicate=false（recipe 结构与后端验证非同因）,
  trigger_overlap=false（G1/CMake 迁移 trigger 不同）, solution_overlap=false（无既有
  条目给出“验证汇编后端被选中”的测试方法）, combination_novelty=true（header-library
  配方 + aarch64 asm 后端验证 + 鸿蒙专项测试组合无既有覆盖）, boundary_novelty=true
  （边界=上下文切换类单文件库后端选择验证，既有条目仅覆盖纯 header 安装结构）,
  test_migration_novelty=true（新增 15 断言鸿蒙专项测试用例，非上游测试复述）
- 关系字段: similar_to=E257/E321/E322/E470（header-only 配方部分）,
  caused_by=无, prerequisite_of=无, conflicts_with=无

## 候选 C：init-build URL 搜索给出同名不同项目候选
- 真实错误: `init-build` 搜索引擎给出 4 个 URL（savannah/waterlan 的 "minicoro"），
  均为同名不同项目（网络流量计费工具），非 edubart/minicoro 官方协程库
- 根因: 搜索引擎按包名匹配，同名不同项目会进入候选列表；任务正文明确官方来源
  `https://github.com/edubart/minicoro`
- 修复: 按任务「官方来源」约束拒绝搜索候选，改用官方 GitHub tag tarball
  （`archive/refs/tags/v0.1.3.tar.gz`，SHA-256
  `4f9d4c3b5f6473f8141ee45e9947a6e7e7ee6665b4d9a8c373c0602495c5f6c9`，两次下载一致）
- 验证: conandata 使用官方 URL，conan create / W3 全部通过
- 适用范围: 任何 init-build 搜索候选与任务官方源冲突的场景
- 查重: **部分覆盖/复用** — R39（源码 URL 必须为官方源）+ E299（classify-source-failure）
  + E231（discover-tests-from-verified-archive）已覆盖官方源优先与校验原则；本候选是
  “搜索候选命中同名不同项目”的新触发场景，但根因（官方源约束）与方案（坚持官方源）
  已被覆盖 → **reuse_existing**（R39），不单独新建草稿

## R02 新增候选 D：CI R40 分支命名硬门禁——版本 slug 不得带上游 v 前缀
- 真实错误: R01 交付后远端 CI /rebuild 在 L0n（R40）失败，CI 原文：
  ```
  [step] L0n: Checking branch name matches package (R40)...
  [error] L0n: branch name mismatch (R40) — 分支完全不包含 包名-版本号
         分支 'feat/minicoro-v0.1.3'（去前缀后 'minicoro-v0.1.3'）不包含 'minicoro-0.1.3'
  [hint] 分支名必须以 包名-版本号 结尾，例如：minicoro-0.1.3 / feat/minicoro-0.1.3 / fix/minicoro-0.1.3
  [fail] minicoro/0.1.3 — L0 quality gate failed: branch_name_r40
  L0_RESULT=fail: gate failed: branch_name_r40
    Pass rate: 0.0% (0/1)
  ```
- 根因: 注册表版本 slug 为 `0.1.3`（`archives/m/minicoro/0.1.3`、`minicoro/0.1.3`），
  `v0.1.3` 仅是上游 tag；R01 任务把 tag 误用为版本 slug 写入分支
  `feat/minicoro-v0.1.3`，违反 CI L0n/R40 分支命名硬门禁（分支必须精确以
  `包名-版本slug` 结尾，去前缀后逐字节相等，不允许额外后缀）
- 修复: 在唯一专用 worktree 内 `git branch -m feat/minicoro-v0.1.3 feat/minicoro-0.1.3`，
  推送新分支 `origin/feat/minicoro-0.1.3`；本地 L0n 校验模拟通过
  （`feat/minicoro-0.1.3` → 去前缀 `minicoro-0.1.3` == 期望 tag）；PR #10661 head
  切换遇到平台限制（v5 PATCH 不接受 head/source_branch 字段、PUT 405、v4 403 禁用、
  PR 已 closed 且 can_reopen=false），按恢复规则记录平台行为并继续
- 验证: `git branch --show-current` = `feat/minicoro-0.1.3`；L0n 校验脚本逻辑
  （去前缀+逐字节比较）PASS；新分支已推送 origin（commit 7c077f58）
- 适用范围: 任何上游 tag 带 `v` 前缀而注册表版本 slug 不带（`v0.1.3`→`0.1.3`）的库，
  在 CI L0n/R40 分支命名门禁下的分支命名；以及 tag 大小写与 slug 不一致的场景
- 反例: 上游 tag 与注册表 slug 一致（如 `1.2.3` tag == `1.2.3` slug）时不适用；
  分支带额外后缀（`-ASDH`）属另一错误模式（L0n 后缀拦截），方案不同
- 查重: **部分覆盖/新增差异** — E999-draft-35E4（prover9）= 大写 tag→小写 slug +
  L0n 分支名精确匹配，覆盖"分支名必须等于 slug"原则；但**未覆盖**"上游 tag 的
  `v` 前缀必须剥离、不得进入版本 slug 与分支名"这一触发场景（v 前缀剥离）
- 七轴查重: exact_duplicate=false（无 v 前缀剥离条目）,
  causal_duplicate=false（prover9 根因是 Conan 全小写约束，本候选根因是 tag/slug
  语义混淆）, trigger_overlap=false（prover9 触发于 conan create G2，本候选触发于
  CI L0n）, solution_overlap=true（部分：分支名 = slug 精确匹配原则与 E999 相同）,
  combination_novelty=true（v 前缀剥离 + L0n 分支门禁组合无既有覆盖）,
  boundary_novelty=true（边界 = tag 的 v 前缀 vs 注册表 slug，E999 未展开）,
  test_migration_novelty=false（无新测试迁移）
- 关系字段: similar_to=E999-draft-35E4（分支名=slug）、E416（分支/目录命名一致性）,
  caused_by=CI L0n/R40 分支命名门禁, prerequisite_of=无, conflicts_with=无

## R02 候选 D 补充：PR head 切换平台限制（分支改名后）
- 真实错误/行为: 分支改名+推送后，尝试把现有 PR #10661 的 head 切到新分支，
  平台 v5 API 不支持（PATCH /pulls/{number} 仅接受 title/body/state/milestone/
  labels/draft 等字段，head/source_branch 被忽略或 400；PUT → 405；
  /api/v4 接口禁用 403；无分支 rename 端点）；PR 状态 closed 且项目设置
  can_reopen=false 无法重开
- 修复: 按 R02 恢复规则 #2「分支改名或 PR head 更新遇到平台限制：记录具体
  API/命令、退出码与平台行为，按受限最小动作继续」——记录证据、不 force-push/
  rebase/merge、不关闭重建 PR；旧远端分支在确认 head 跟随前不删除
- 验证: PATCH head 多次 200 但 GET head.ref 仍为旧分支名；PUT 405；
  PATCH 报错字段表不含 head/source_branch；GET 显示 closed_at/can_reopen=false
- 查重: **未覆盖/平台行为记录** — 知识库无 PR head 切换平台限制条目；
  sipsak/asterisk-flite 归档 notes 记录了同类"PR head 由 HMBS 后端在预检通过后
  统一推送更新"的平台行为 → 以 notes 形式补充，不单独建草稿
- 决定: 记录为 notes 平台行为（并入候选 D 草稿的关系与恢复条件），不建独立草稿

## 路径判定（B 七轴汇总）
- 候选 A: reuse_existing（既有基线噪声草稿完全覆盖）
- 候选 B: **new_draft**（部分覆盖、新增差异已验证可跨库复用）→ 触发路径 B
- 候选 C: reuse_existing（R39 覆盖）
- 候选 D (R02): **new_draft**（v 前缀剥离场景新增差异）→ 触发路径 B
- **路径决定: 路径 B（知识库扩展）** — 候选 B 与候选 D 成立，分别新建
  DRAFT-minicoro-0.1.3-aarch64-asm-backend-verification 与
  DRAFT-minicoro-0.1.3-r40-branch-naming-vslg .md/.kv 草稿配对，
  与 minicoro 归档同 PR 交付（任务类型=知识库扩展，PR 前缀【知识库扩展】）
