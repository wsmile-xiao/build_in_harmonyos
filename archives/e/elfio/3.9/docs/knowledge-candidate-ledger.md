# Knowledge Candidate Ledger — elfio 3.9（R02 提交版）

**任务**: elfio-3.9-r02-evidence-knowledge-delivery-pc3-7-20260905T061500Z
**范围**: 证据修复轮——完整候选台账 + 四范围查重 + 七轴判定 + 关系字段
**执行端权威目录**: 当前 worktree 根目录（knowledge/graph/index.tsv、knowledge/doc/、knowledge/graph/、knowledge/drafts/、ohc-run.py engine）

## 候选 1: W3 junk_check 整仓扫描回退连坐其他库历史基线（.ci-trigger）

- **真实错误**: `finish elfio 3.9 built` Step5 W3 首次失败，`检查模式: full`，
  `[FAIL] JC5: archives/u/util-linux-login/2.42.2/.ci-trigger` 未登记隐藏文件，
  `JC_RESULT=fail → L0_RESULT=fail: junk_check failed`。
- **根因**: junk_check 三优先级 prdiff→incremental(`git diff origin/main...HEAD`)→full(`git ls-files`)；
  分支本地提交前 diff 为空 → 回退 full 整仓扫描 → 命中 main 上 util-linux-login PR 遗留的
  已跟踪空文件 `.ci-trigger`（sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855）。
- **修复/验证**: 提交本库归档后 W3 走 incremental（R02 实测 11 文件）→ `Junk Files: 0` 通过；
  基线路径未改动、未包含、哈希记录、原样保留（R02 复核：不在本库 diff，文件仍在，哈希一致）。
- **四范围查重**:
  - 正式知识 doc/: 无 junk_check/full-scan 条目。
  - 图谱 index.tsv: 无 junk_check/整仓扫描条目。
  - 草稿 drafts/: **DRAFT-libfort-0.4.2-w3-baseline-junk-check-full-scan(.md/.kv) 与
    DRAFT-libpopcnt-2.0-w3-baseline-junk-check-full-scan(.md/.kv) 完整覆盖**（同根因、
    同触发条件、同方案：范围限定当前库 diff + 基线噪声精确隔离/哈希恢复）。
  - engine: 无额外命中。
- **七轴**:
  - exact_duplicate: false（不同库、不同基线路径）
  - causal_duplicate: **true**（同根因：full-scan 回退连坐基线文件）
  - trigger_overlap: **true**（同触发：diff 为空回退 full）
  - solution_overlap: **true**（同方案：提交后 incremental / 隔离豁免）
  - combination_novelty: false
  - boundary_novelty: false
  - test_migration_novelty: false
- **关系**: similar_to=DRAFT-libfort-0.4.2/DRAFT-libpopcnt-2.0；caused_by/prerequisite_of/conflicts_with=无
- **结论**: **完整重复（causal+trigger+solution 全重叠）→ 复用既有草稿，不建新草稿**。
  既有条目已覆盖；本轮仅新增一个基线路径实例（.ci-trigger），无独立可复用差异。

## 候选 2: Conan profile 相对路径被 ~/.conan2/profiles 同名路径遮蔽（os.version 缺失）

- **真实错误**: `conan create ... -pr=ci/conan/profiles/ohos-aarch64` 报
  `elfio/3.9: Invalid: 'settings.os.version' value not defined`；
  `conan profile show` 显示 host profile 无 os.version、libcxx=libstdc++11、
  cppstd=gnu14（与 worktree 内官方 profile 文件内容不符）。
- **根因**: 本机 `~/.conan2/profiles/ci/conan/profiles/ohos-aarch64` 存在**同名嵌套路径**
  的旧 profile（无 os.version、libstdc++11），`-pr=` 相对路径解析优先命中该 home 副本，
  而非 worktree 内 `ci/conan/profiles/ohos-aarch64`；OHOS settings.yml 要求 os.version
  必须定义（["5.0","6.0"]），缺失即 `Invalid: 'settings.os.version' value not defined`。
- **修复/验证**: 改用绝对路径 `-pr:h=$(pwd)/ci/conan/profiles/ohos-aarch64
  -pr:b=$(pwd)/ci/conan/profiles/ohos-aarch64` 强制指向 worktree 官方 profile →
  conan create + test_package（双测试）+ conan-verify 全 PASS（R02 实测重跑，exit=0）。
- **四范围查重**:
  - 正式知识 doc/: E455（libcxx 误配，根因=profile 内容错误，修法=换 libc++）为**不同机制**；
    E364/E540 均非 profile 路径解析；无 os.version/相对路径遮蔽条目。
  - 图谱 index.tsv: 无 profile 路径解析/遮蔽关键词。
  - 草稿 drafts/: 无 os.version/相对路径遮蔽草稿。
  - engine: 命中 E455（Phase B）但根因/方案均不同，非覆盖。
- **七轴**:
  - exact_duplicate: false
  - causal_duplicate: false（E455=profile 内容误配；本候选=profile 路径解析遮蔽，机制不同）
  - trigger_overlap: 部分（都涉 conan profile 使用；触发点不同：内容 vs 路径）
  - solution_overlap: 无（E455 换 libc++ profile；本候选用绝对路径 -pr:h/-pr:b）
  - combination_novelty: false
  - boundary_novelty: **true**（仅当 ~/.conan2/profiles 存在同名嵌套路径时相对路径失效；
    CI/无遮蔽环境不受影响；绝对路径可绕开）
  - test_migration_novelty: false
- **关系**: similar_to=E455（conan profile 相关）；caused_by/prerequisite_of/conflicts_with=无
- **适用边界/反例**:
  - 适用: 本机 ~/.conan2/profiles 下存在与相对路径同名的嵌套副本、且 settings.yml 对 os
    定义必填子项（OHOS 的 os.version）时必然触发。
  - 反例: CI 环境（无该遮蔽）；非 OHOS os（os.version 非必填）不受影响；显式绝对路径
    指定可完全绕开；若 home 副本与 worktree 内容一致则无失效表现。
- **结论**: **未命中 + 新增差异（路径解析遮蔽→绝对路径修复）已由本轮真实日志验证、
  可跨库复用（所有 OHOS 库 conan create 均适用）→ 路径 B，保留 DRAFT 草稿
  （.md/.kv 同 stem 配对，已提交）**。

## 候选 3: ELFIO 3.9 release 包不含 tests/、Boost 测试框架缺失（上游测试硬阻塞）

- **真实错误（R01/R02）**: `fatal error: 'boost/test/included/unit_test.hpp' file not found`；
  `conan download boost/1.84.0 -r=ohpcd` 失败（远端不可达）。
- **R03 复核新证据（本轮更新）**: 改用任务指定 `boost/1.90.0.2.1` 复核——
  - `conan list 'boost/1.90.0.2.1' -r=ohpcd` → **注册表存在**（canonical: boost/1.90.0.2.1，
    revision 80804a28，包 id 01d92cf3…，revision 46ff9a49；未替换为 1.84.0）。
  - `conan download 'boost/1.90.0.2.1' -r=ohpcd`（--only-recipe + 完整包）→ dl_rc=0。
  - 包内容: include/boost 顶层 195 条目，但**无 boost/test 目录**；`unit_test.hpp` 与
    `included/unit_test.hpp` 均不存在；recipe 无 `unit_test_framework` 组件/CMake target。
  - 真实编译尝试（-I boost 包 include）→ 首错仍为 `'boost/test/included/unit_test.hpp' file not found`，
    compile_rc=141。证据日志: evidence/boost_dependency_audit.log（SHA-256 3159ddc4…）。
- **根因/归属**: 上游 release tarball 仅含 examples/ 无 tests/（git tag 才有）；tests/ 依赖
  Boost.Test 头，而 OHOS registry 的 boost/1.90.0.2.1 **包内不含 boost/test 头**（包内容缺失）
  → 依赖/基础设施阻塞（L0i 依赖可用性门禁），非 elfio 适配缺陷。
- **四范围查重**: 无既有条目；属 L3 本版笔记 + 依赖阻塞记录（已入 docs/upstream-test-ledger.md
  与 MANIFEST.yml）。
- **七轴复核（R03 新证据不改变判定）**:
  - exact/causal/trigger/solution_overlap: 均不适用（非适配知识，属包内容可用性事实）
  - combination_novelty: false｜boundary_novelty: false｜test_migration_novelty: false
  - 该事实为注册表/包内容状态，非可复用适配技术，不构成跨库知识条目。
- **R04 证据更新（本轮）**: 任务改用 `boost/1.90.0` 后包内**含 Boost.Test 头**
  （`boost/test/included/unit_test.hpp`、`boost/test/unit_test.hpp` 存在，recipe 定义
  `Boost::unit_test_framework` 组件），36 个上游用例**全部编译运行通过（36/36, 100%）**，
  候选 3 的"Boost 缺失硬阻塞"状态已解除——该事实属依赖可用性随 registry 包内容变化，
  仍非适配技术知识（L3 笔记 + 台账已如实更新，见 docs/upstream-test-ledger.md §0b）。
- **结论**: 保持 **不建草稿**（L3 笔记 + 台账已覆盖）；不建重复条目。

## 候选 4: ELFIO 3.9 elf_types.hpp 未定义 EM_AARCH64

- **真实错误**: test_harmonyos_elf.cpp 编译报 `use of undeclared identifier 'EM_AARCH64'`。
- **根因/修复**: ELFIO 3.9 头文件未含 EM_AARCH64（183），本地 `#define EM_AARCH64 183`
  后编译运行通过。
- **四范围查重**: 无既有条目；库特有 API 事实（L3 本版笔记，入 notes.md）。
- **结论**: 本库专属，不符合"可跨库复用"建草稿门槛，**不建草稿**。

## 候选 5: header-only CMake INTERFACE 库的 Conan 2 配方模式

- **真实证据**: elfio 3.9 为 header-only（package_type=header-library、INTERFACE 目标、
  cpp_info.includedirs、test_package 消费者验证），配方与 boolean-lite 等 lite 系一致。
- **四范围查重**: **E321（martinmoene lite 系 header-only Conan 2 迁移）已完整覆盖**
  （index.tsv 547 行在列，doc/E321.md 存在，关键词 header-only/package_type=header-library/CTest）。
- **结论**: **reuse_existing（复用 E321）**，不建草稿。

## 路径判定（R02，R04 复核）

- R04 复核：新证据（boost/1.90.0 可用、36/36 通过）仅更新候选 3 的证据字段，不改变候选 2（new_draft）七轴判定；不建重复条目。

- 候选 2 满足"已验证 + 可跨库复用 + 查重未命中/部分覆盖 + 新增差异" → **路径 B 成立**。
- 候选 1 完整重复（复用既有 libfort/libpopcnt 草稿）；候选 3/4/5 为 L3 笔记或既有条目复用。
- **路径结论: new_draft（候选 2）→ 知识库扩展，PR 前缀【知识库扩展】**
  （与任务头 initial_pr_prefix 依 new_draft 规则切换一致）。草稿同 stem .md/.kv 见
  knowledge/drafts/（已随分支提交）。
