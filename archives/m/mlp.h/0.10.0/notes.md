# mlp.h 0.10.0 适配笔记

## 一、上游测试完整枚举台账（R51 / 双口径）

### 枚举统计
- 源码：官方 tag v0.10.0（git commit 61a5a5e73344f1dfa023fedd5e2e303312cac50c）tar.gz，SHA-256 = `54b1be6fae01b313fbc19dce059882120f2f762bb381c55ac560c39ecd842b00`，共 16 个文件。
- **用户测试源：无**。上游不存在 tests/ 目录、无任何测试框架（无 doctest/catch2/CUnit/libtap 等）、MLP.h 内无 TEST_CASE/assert 等测试宏（`grep -E 'TEST|assert' MLP.h` 零命中）、无 ctest/pytest/meson test 注册项。
- **独立上游用例（source_declared_total）= 0**。

### 逐项台账

| 入口 | 类型 | 是否独立上游用例 | 分类理由 | 是否实际运行 | 结果 |
|---|---|---|---|---|---|
| examples/xor_gate.c | 样例 | 否 | 样例，非测试框架用例 | ✅ 编译+运行 | rc=0，训练收敛，XOR 四位真值 0.036/0.988/0.988/0.009，正确保存 xor.mlp |
| examples/visual_sin.c | 样例 | 否 | 样例 | ✅ 编译+运行 | rc=0，5000 epochs 收敛，Final Loss 1.06e-04 |
| examples/load_csv.c | 样例 | 否 | 样例（依赖 datasets/circle.csv fixture） | ✅ 编译+运行 | rc=0，CSV 加载并训练输出正确 |
| examples/load_model.c | 样例 | 否 | 样例（依赖先前保存的 xor.mlp） | ✅ 编译+运行 | 初跑因 cwd 无 xor.mlp 报 "Could not open file"（rc=1），在生成模型目录重跑 rc=0，加载并复现正确 |
| examples/mnist.c | 样例（基准类） | 否 | 样例/基准；需要外部数据集 mnist_train.csv(110MB)/mnist_test.csv(18MB) | ✅ 编译+运行(2次) | rc=124（300s 观察窗口截断），训练正常收敛：run1 Epoch33/50 Loss 3.86e-02，run2 Epoch38/50 Loss 3.06e-02；最终准确率打印未及观察窗口 |
| datasets/circle.csv | fixture | 否 | 数据文件，被 load_csv 消费 | ✅ | 加载成功 |
| MLP.h 头文件 | 框架头 | 否 | 库头文件，无测试宏 | — | 编译期验证通过 |
| docs/api.md getting_started.md theory.md | 文档 | 否 | 非可执行 | — | — |
| 构建目标 | 无 | 无 | header-only，无构建系统 | — | — |

### 双口径统计
- **source_declared_total = 0**（上游无独立测试用例声明；清点证据：无 tests 目录、无测试框架、MLP.h 无测试宏、无 ctest/pytest 注册）
- **configured_executable_total = 0**（当前配置无实例化测试目标；5 个样例非测试注册项）
- **executed_passed_total = 0**；上游用例通过率 = 0/0（无用例可计）
- 补充实际执行口径：5 个可执行样例全部编译成功，4 个完整运行 rc=0，mnist 两次真实运行均正常收敛但超 300s 观察窗口截断（Loss 3.86e-02→3.06e-02，属样例/基准不计入独立用例通过率）

### mnist 恢复规则处置
- 外部数据集首次查询：pjreddie.com → 301 → data.pjreddie.com，Content-Length 109575994/18289443 可下载，已实际下载并按上游预期路径放入 `datasets/`，恢复配置运行成功（训练收敛）。
- 截断原因：单次 Bash 观察窗口 300s 上限（训练需更长时间全量跑完 50 epochs），非编译/平台故障；样例训练本身验证通过。

## 二、环境与构建
- 编译器：clang 15.0.4（`-std=c99 -O2`；visual_sin 因上游使用 `M_PI` 需 `-std=gnu99`，非源码修改）
- 平台：HarmonyOS PC（arm64 目标）；本机执行环境 Linux 用户态
- header-only：无 configure/make，仅 `#define MLP_IMPLEMENTATION` 单编译单元包含

## 三、适配决策
- 打包形态：header-only 库（变体 A），仅拷贝 MLP.h → include/，LICENSE → licenses/，无编译产物，无 commands.json（R38：库类型不需要）
- 依赖：零外部依赖（可选 MLP_USE_LIBM，mlp 样例用到 `<math.h>`，系统库）
- 门禁证据日志目录：`$TMPDIR/oh-pc1-6-mlp/`（各门禁日志独立、SHA-256 见最终回报）

## 四、知识候选台账（knowledge_candidate_ledger）与路径判定

### 候选清单（非噪声项）

| # | 候选 | 真实错误 | 根因 | 修复 | 验证 | 适用范围 | 决定 |
|---|---|---|---|---|---|---|---|
| C1 | header-only 配方 package() copy() 相对 dst 陷阱 | conan create "No files in this package!" / test_package 找不到 MLP.h | Conan 2 copy() 相对 dst 相对 build 目录解析 | copy() 用 `os.path.join(self.package_folder, "include")` 绝对路径 | conan create G2 PASS（mlp.h 本轮实测） | 所有 header-only/copy-based 配方 | **复用既有知识**（DRAFT-boost-te-1.0.0-headeronly-copy-abs-path-commit-incremental 已完整覆盖）→ 路径 A |
| C2 | 新库分支基线不一致致 junk_check 误判 | W3 JC6 "本 PR 涉及 107 个软件包" | 本地 main 领先 origin/main 214 提交（origin/main 引用陈旧），`git diff origin/main...HEAD` 含他库包 | `git fetch origin main` 刷新引用 + `git reset --mixed origin/main` 把分支基线对齐真实远端 + 提交本库文件使检查回退 incremental | W3 重跑 "检查模式: incremental"，JC_RESULT=pass（本轮实测） | 共享 build_in_harmonyos 仓库新库分支 | **复用既有知识**（DRAFT-boost-te 已覆盖 commit-first/基线噪声同族根因）→ 路径 A；本轮新增"陈旧的 origin/main 引用需先 fetch+reset 基线"边界差异，随 C3 草稿记录 |
| C3 | Conan 2.x `self.run(..., check=True)` → TypeError | `TypeError: ConanFile.run() got an unexpected keyword argument 'check'` | Conan 2 已移除 check 参数（默认非零即抛） | 删除 `check=True` | conan create test_package PASS（本轮实测） | 所有 Conan 2 test_package 配方 | **new_draft**（路径 B）→ 建 DRAFT-mlp.h-0.10.0-conan2-testpkg-check-kwarg 草稿对 |
| C4 | 严格 C99 下 M_PI/_USE_MATH_DEFINES 未定义 | `visual_sin.c: use of undeclared identifier 'M_PI'` | _USE_MATH_DEFINES 是 MSVC 宏，clang 严格 c99 不导出 M_PI | 编译改用 `-std=gnu99`（非源码修改） | visual_sin 编译+运行 PASS（本轮实测） | 任何在 clang 严格 c99 下使用 M_PI 的上游 C 样例 | **new_draft**（路径 B）→ 并入 C3 同草稿对 |

### 四范围查重（正式 E 条目 / 图谱 / 草稿 / doc）

- **C1**：E340（basic_layout+cargo 产物路径）部分相关但场景不同（cargo 定位 vs copy dst 解析）；E311（source_folder 隔离诊断）不同主题；DRAFT-boost-te 已**精确覆盖**（标题同根因同方案）→ `exact_duplicate=true`，复用既有草稿。
- **C2**：E255（数据包适配）无关；DRAFT-dr_mp3 / DRAFT-kdbusaddons / DRAFT-boost-te 的 baseline-noise 同族 → `causal_duplicate=partial`（根因同源：junk_check 基线），`boundary_novelty=true`（本轮触发面是陈旧的 origin/main 引用导致 107 包 JC6，而非零提交 full 模式）。复用既有草稿 + 差异随 C3 草稿记录。
- **C3**：E239 覆盖 self.run fail-fast 语义，但**未覆盖 check= 参数被移除**（TypeError 面不同）；E600-draft（HMDFS build-user 目录）无关；图谱/doc 均无 `check=True` 关键字命中 → `exact_duplicate=false, causal_duplicate=false, trigger_overlap=false, solution_overlap=false, combination_novelty=true, boundary_novelty=true, test_migration_novelty=false`。
- **C4**：图谱精确检索 `M_PI|_USE_MATH_DEFINES` 零命中（E062/E117 为 FLEXIBLE_ARRAY_MEMBER/PACKAGE_STRING，不同主题）；草稿无 M_PI 条目 → 未命中，新增差异成立。

### 七轴查重汇总（C3+C4 合并草稿）

| 轴 | C3 (self.run check=) | C4 (M_PI gnu99) |
|---|---|---|
| exact_duplicate | false | false |
| causal_duplicate | false | false |
| trigger_overlap | false | false |
| solution_overlap | false | false |
| combination_novelty | true | true |
| boundary_novelty | true | true（严格 c99 边界） |
| test_migration_novelty | false | false |

关系：similar_to=[E239, E311, E340, DRAFT-boost-te-1.0.0-headeronly-copy-abs-path-commit-incremental]；caused_by=[]；prerequisite_of=[]；conflicts_with=[]。

### 路径判定
- `reuse_existing`：C1、C2（复用 DRAFT-boost-te-1.0.0-headeronly-copy-abs-path-commit-incremental）
- `new_draft`：C3+C4 → DRAFT-mlp.h-0.10.0-conan2-testpkg-check-kwarg 草稿对（.kv/.md 同 stem）
- **路径 B（知识库扩展）成立**：存在已验证、可跨库复用、查重未命中的新增差异（Conan 2 test_package 配方 API 变化 + 严格 C99 M_PI 编译边界），草稿与本库归档进同一 PR。
---

**编译结束**: 2026-10-04 19:53
**最终状态**: built
