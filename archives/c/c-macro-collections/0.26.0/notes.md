# c-macro-collections 0.26.0 适配笔记

## 编译环境
- 构建系统: makefile（header-only 宏库，无 configure/CMake install 目标；顶层 Makefile 仅驱动 tests/benchmarks）
- 编译日期: 2026-09-22
- 编译器: clang 15.0.4（aarch64-linux-ohos 交叉工具链）
- 状态: built

## 编译步骤

header-only C11 宏库：src/cmc/ 下 16 个主头文件 + cmc/cmc/<name>/ 实现子目录 + cmc/utl/ 工具头 + cmc/cor/ 核心头，无任何 .c 编译单元。配方仅安装头文件树：

1. `ohc-run.py init-build c-macro-collections 0.26.0 --url=<官方 GitHub v0.26.0 tarball>`
2. `ohc-run.py conan-init c-macro-collections 0.26.0` → 生成配方后改写为 header-library 类型（无编译单元，package() 复制 src/cmc → include/）
3. `ohc-run.py conan-verify c-macro-collections 0.26.0` → G0-G4 + L2/L4/L5 全部 PASS

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-init 生成 autotools 模板 | 库实为 header-only，无 configure 脚本 | 改写 conanfile.py 为 package_type=header-library，package() 用 `copy(self, "cmc/**", src, include)` 递归收纳头文件树 |
| 2 | G2 首次失败 "No files in this package!" | copy pattern `"cmc"` 只匹配目录不匹配文件 | 改为 `"cmc/**"` 递归复制（130 个头文件全部打包） |
| 3 | test_package 编译失败：`cmc_i32_cpy/free/pri` 未声明 | futils.h 对 int 类型仅提供 cmp/str/hash；cpy/free 可空 | fval 表 .cpy=NULL、.free=NULL、.pri=cmc_i32_cmp（与上游 unt_list.h 同款用法） |
| 4 | test_package 编译失败：`intl_iter_end(&it)` 参数类型错 | 迭代器终止判断 API 是 `intl_iter_at_end(&it)`（`_iter_end(list)` 返回迭代器） | 改用 `intl_iter_at_end` |
| 5 | conan-verify 引擎误命中 E529/E540/E092（waf/imp、cmake 平台、runner-path） | 引擎关键词匹配噪声 | 均为误匹配；实际首错已在本地修复，G2 最终通过 |

## 源码修改

无补丁（header-only 库零修改；patches/ 为空）。

## 依赖版本

零依赖（header-only，`requirements()` 为空）。工具链：clang 15.0.4 + llvm-ar/ranlib + make/cmake。

## 上游测试完整枚举台账（R51 双口径）

**测试源清点**（tests/ 目录，官方 tag v0.26.0 源码）：

| 测试入口 | 类型 | 是否独立上游用例 | 说明 |
|---------|------|----------------|------|
| tests/main.c | 用户测试源（聚合入口） | 否（聚合器） | 包含 17 个 unt_*.h 测试头，注册 33 个测试单元（16 集合 × 2 + ForEach），实际编译运行 |
| tests/unt_bitset.h | 用户测试源 | 是（19 用例） | CMC_CREATE_TEST 宏定义用例，随 main.exe 实际执行 |
| tests/unt_deque.h | 用户测试源 | 是（41 用例） | 同上 |
| tests/unt_hashbidimap.h | 用户测试源 | 是（25 用例） | 同上 |
| tests/unt_hashmap.h | 用户测试源 | 是（38 用例） | 同上 |
| tests/unt_hashmultimap.h | 用户测试源 | 是（29 用例） | 同上 |
| tests/unt_hashmultiset.h | 用户测试源 | 是（24 用例） | 同上 |
| tests/unt_hashset.h | 用户测试源 | 是（42 用例） | 同上 |
| tests/unt_heap.h | 用户测试源 | 是（27 用例） | 同上 |
| tests/unt_intervalheap.h | 用户测试源 | 是（25 用例） | 同上 |
| tests/unt_linkedlist.h | 用户测试源 | 是（21 用例） | 同上 |
| tests/unt_list.h | 用户测试源 | 是（40 用例） | 同上 |
| tests/unt_queue.h | 用户测试源 | 是（41 用例） | 同上 |
| tests/unt_sortedlist.h | 用户测试源 | 是（25 用例） | 同上 |
| tests/unt_stack.h | 用户测试源 | 是（37 用例） | 同上 |
| tests/unt_treemap.h | 用户测试源 | 是（19 用例） | 同上 |
| tests/unt_treeset.h | 用户测试源 | 是（17 用例） | 同上 |
| tests/unt_foreach.h | 用户测试源 | 是（14 用例） | 16 处 CMC_CREATE_TEST 中 2 处（BitSet/HashBidiMap）为注释禁用，活跃 14 用例，全部随 main.exe 执行 |
| tests/utl.h | 测试辅助头 | 否 | assert/工具宏，非独立用例 |
| tests/tostring.h | 测试辅助头（to_string 目检） | 否 | 非独立用例 |
| tests/single.c | 开发辅助入口 | 否 | `make dev/single` 单用例调试入口，非独立用例集合 |
| tests/types.c | 视觉检查程序 | 否（辅助） | to_string 目检，可编译运行（exit 0），非 CMC_CREATE_TEST 用例 |
| benchmarks/ | 基准（非测试） | 否 | benchmark.c 性能基准，不计入用例 |
| examples/ | 样例（非测试） | 否 | 9 个示例程序，不计入用例 |
| 框架头 src/cmc/utl/test.h 等 | 框架源码 | 否 | CMC_CREATE_TEST 宏定义处，不计为用例 |

**双口径统计**：

- `source_declared_total`：484（官方 tag 源码 tests/ 17 个 unt_*.h 中按 `CMC_CREATE_TEST` 可复制枚举规则发现的活跃用例声明总数；486 处字面匹配 − unt_foreach.h 2 处注释禁用）
- `configured_executable_total`：484（main.c 实例化 17 个测试头全部活跃用例，构建为单一 main.exe，33 个测试单元）
- `executed_passed_total`：484（全量实际运行通过）
- 失败：0
- 未运行/未实例化：0（无互斥编译分支排除；2 处注释禁用项为源码内注释，不计入声明总数）
- 断言：611330/611330 通过（0 失败）
- 全量通过率：484/484 = 100%；当前配置可执行集合通过率：484/484 = 100%

**逐项映射**：`源码 CMC_CREATE_TEST 声明（17 头 484 项）→ 无预处理条件排除（main.c 无条件包含全部 17 头）→ main.c 注册 33 单元 → main.exe 单一可执行 → 实际执行 484 项全过`。

**运行命令与证据**（实测，clang 15.0.4）：

```bash
cd tests && clang -Wall -Wextra -g -O0 -I ../src main.c -o out/main.exe && ./out/main.exe
# 33 单元 484 用例全部 PASSED，断言 611330/611330，exit 0
# 日志: $HOME/tmp/oh-runner-cmc/tests-run/upstream-main-run.log
```

## 验证结果

- conan-verify：G0/G1/G2/G3/G4 + L2/L4/L5 全部 PASS（报告: reports/conan-verify-report.md）
- 上游测试：484/484 通过（100%），断言 611330 全过
- test_package 消费者用例：编译 + 运行通过（见 test_package/test.c）

## 交付物

header-only 包（无 bin/lib 产物）：conanfile.py + conandata.yml + test_package/ + 130 个头文件。

## 注意事项

- header-only 宏库：`#define V/PFX/SNAME 后 #include "cmc/list.h"` 使用；扩展功能需先定义 CMC_EXT_* 宏（与上游文档一致）。
- 消费者用例 fval 表对基本类型：.cpy/.free 可 NULL（上游 unt_list.h 同款）。
- 迭代器终止判断用 `PFX##_iter_at_end(&it)`。

## 知识候选台账（knowledge_candidate_ledger）

| # | 候选（真实错误→根因→修复→验证） | 适用范围 | 查重结果 |
|---|------|----------|----------|
| K1 | G2 "No files in this package!" → conan.tools.files.copy() 按文件 glob 匹配，目录 pattern（"cmc"）不递归 → 改 `copy(self, "cmc/**", src, dst/include)` 递归复制，130 头文件打包，G2 通过 | 无 CMake install 目标、package() 需手动安装头目录的 header-only 库（Conan 2） | 四范围：正式 doc/ 未命中该具体方案；图谱 index.tsv 未命中；草稿 drafts/ 已存在 DRAFT-emio-0.9.0-conan-copy-dir-recursion（推荐 shutil.copytree）与 DRAFT-gulrak-filesystem-1.5.8-headeronly-copy-nested-include（推荐 ghc/*.hpp 子目录模式，fallback 已含 `**/*.hpp`）→ **部分覆盖，我的 `dir/**` glob 方案是 gulrak fallback 的同款落地，无新增差异** |
| K2 | test_package 编译：cmc_i32_cpy/free/pri 未声明 → futils.h 对 int 仅提供 cmp/str/hash → fval 表 .cpy/.free=NULL、.pri=cmp（上游 unt_list.h 同款） | 该库宏 API 使用细节 | 库特定用法，已写入 notes.md/manifest knowledge_gained；非跨库知识 |
| K3 | 迭代器终止判断 `PFX##_iter_end(&it)` 参数类型错 → ext API 是 `_iter_at_end(&it)` | 该库宏 API 使用细节 | 库特定用法，已写入 notes.md；非跨库知识 |

**七轴查重（K1 为主候选）**：

| 轴 | 结论 |
|----|------|
| exact_duplicate | 否（不同库不同代码） |
| causal_duplicate | 是（copy() glob 不递归目录，与 emio/gulrak 草稿同根因） |
| trigger_overlap | 是（G2 "No files in this package!" / Imported target 路径不存在） |
| solution_overlap | 是（gulrak fallback 已记载 `**/*.hpp` 模式，我的 `dir/**` 为同款落地） |
| combination_novelty | 否（无新组合） |
| boundary_novelty | 否（C 宏库多层嵌套头树与 include/<subdir> 属同类边界） |
| test_migration_novelty | 否（无新测试迁移洞察） |

**关系字段**：K1 `similar_to` DRAFT-emio-0.9.0-conan-copy-dir-recursion、DRAFT-gulrak-filesystem-1.5.8-headeronly-copy-nested-include；`caused_by` conan.tools.files.copy glob 语义；无 `prerequisite_of`/`conflicts_with`。

**路径决定**：`reuse_existing` → **路径 A**（K1 由既有 emio/gulrak 草稿覆盖，无独立可验证新增差异；K2/K3 为库特定用法非跨库知识）。按任务头 `initial_pr_prefix: 【知识库扩展】` 创建 PR。
---

**编译结束**: 2026-09-22 13:30
**最终状态**: built
