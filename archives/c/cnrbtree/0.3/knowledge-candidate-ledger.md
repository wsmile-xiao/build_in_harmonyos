# cnrbtree 0.3 知识候选台账（knowledge_candidate_ledger）

任务: cnrbtree-0.3-r01-pc2-7-20260921T160949Z · task_type: 知识库扩展
查重范围: knowledge/doc/（正式 E###.md）、knowledge/graph/（E###.kv + index.tsv）、
knowledge/drafts/（草稿 .md/.kv）、knowledge/draft/ 四范围

## 候选 1：raw Makefile 在 recipe 内直接硬编码 `gcc`（无 CC 变量）→ 须改写为 $(CC)
- 真实错误: `make: gcc: No such file or directory` / `make: *** [Makefile:4: testtree] Error 127`
  （OHOS 工具链仅有 clang，无 gcc）
- 根因: cnrbtree 顶层 Makefile 的编译规则直接把 `gcc` 写死在 recipe 体内
  （`gcc -o $@ $^ ...`），Makefile 中不存在 `CC`/`LD` 变量；
  因此 `make CC=clang` 命令行覆盖无效（recipe 不引用 $(CC)），只能改写 recipe。
- 修复: 将 recipe 中 `gcc` 改写为 `$(CC)`（testtree/simple 两条规则），
  以 `make CC=clang` 编译；conan 配方按 R33 从工具链解析编译器。
- 验证: `make CC=clang testtree simple` rc=0；`./testtree`/`./simple` rc=0；
  W3 build_and_test.sh 通过；conan create + test_package 通过（1032 断言全 PASS）。
- 适用范围: 任何在 recipe 体内直接写死编译器名（非变量形式）的 raw-Makefile C 项目，
  在 clang-only 的 OHOS/类环境上适配。
- 查重（七轴）:
  - exact_duplicate: false — 既有条目均针对 `CC := g++` 变量形式
  - causal_duplicate: partial — 同属"Makefile 硬编码编译器名 + OHOS 仅 clang"根因族
    （cohomcalg/0.32 草稿 DRAFT-cohomcalg-0.32-makefile-gxx-override）
  - trigger_overlap: high — 触发一致（`make: gcc/g++: No such file or directory`）
  - solution_overlap: partial — cohomcalg 用命令行覆盖 `CC :=` 变量即有效；
    cnrbtree 因编译器写死在 recipe 内，命令行覆盖无效，必须改写 recipe 为 $(CC)
  - combination_novelty: low
  - boundary_novelty: **yes** — "recipe 内嵌编译器（非变量声明）→ 命令行覆盖无效、
    必须 $(CC) 化"是与既有草稿的明确边界差异，本轮已由真实日志验证
  - test_migration_novelty: no
- 覆盖/新增差异: DRAFT-cohomcalg-0.32-makefile-gxx-override 覆盖"变量形式 CC:=g++
  命令行覆盖"；本轮新增"recipe 内嵌编译器，需改写 $(CC) 再覆盖"场景。
- 关系: similar_to=DRAFT-cohomcalg-0.32-makefile-gxx-override;
  caused_by=无; prerequisite_of=无; conflicts_with=无
- 路径判定: **new_draft**（新增差异已由本轮真实日志验证、可跨库复用）
  → 建同 stem 草稿对: knowledge/drafts/DRAFT-cnrbtree-0.3-makefile-recipe-gcc-hardcode.kv / .md

## 候选 2：单头文件库（CNRBTREE_IMPLEMENTATION 模式）Conan 配方
- 真实错误: 无（无报错）；conan-init 生成 Autotools 模板不适用
- 根因: cnrbtree 是 header-only 单头文件库（`#define CNRBTREE_IMPLEMENTATION` 引入实现），
  无 configure/编译产物；Autotools 模板（configure+make install）不适用。
- 修复: 按本仓已验证 header-only 变体 A 模式（sse2neon/1.9.1 配方）：
  package_type="header-library"、无 build()、package() 直接拷贝 cnrbtree.h+LICENSE、
  package_id() 清空、cpp_info.bindirs/libdirs/libs 置空。
- 验证: conan-verify G1/G2/G3/G4/L1/L4 通过；test_package 消费者用例 1032 断言全 PASS。
- 适用范围: 任何"单头文件 + IMPLEMENTATION 宏"型 C 库。
- 查重: **完全重复/复用** — E035（header-only-install）、E257（no-op-build-for-header-only）、
  E307（header-only compile-only）、E321/E322（header-only Conan2 配方，martinmoene/
  Taskflow 案例）已覆盖同根因与方案；sse2neon 归档即为本仓模板实例
  → **reuse_existing**（复用 E257/E321/E322），不建新草稿

## 路径判定
- 候选 1 已验证、可跨库复用、查重为部分覆盖并存在明确新增差异（recipe 内嵌编译器
  → 必须 $(CC) 化）→ **路径 B（知识库扩展）**，建同 stem .md/.kv 草稿对。
- 候选 2 完全重复 → reuse_existing（复用既有 header-only 条目），不进草稿。
- 决定: **new_draft**（DRAFT-cnrbtree-0.3-makefile-recipe-gcc-hardcode）
