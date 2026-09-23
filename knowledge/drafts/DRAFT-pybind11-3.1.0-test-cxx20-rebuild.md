# DRAFT-pybind11-3.1.0-test-cxx20-rebuild — 上游测试大量 skip 的根因常是"构建标准"而非"头文件缺失"

## 问题（错误签名）
pybind11 3.1.0 上游 pytest 套件首轮实跑出现 51 项 skip，reason 为
`no <optional>` / `no <string_view>` / `no <variant>` / `no <filesystem>` /
`no <barrier>` / `no <ranges>` / `C++17 feature __cpp_inline_variables not
available.` / `C++20 non-type template args feature not available.` 等，
表象像"clang15 libc++ 头文件能力缺口"。

## 根因
测试模块编译 flags（`CMakeFiles/<tgt>.dir/flags.make`）未显式设置
`-std`，clang 15 默认按 **gnu++14** 编译（`__cplusplus=201402L`）：
- C++17/20 特性宏（`__cpp_inline_variables`、`__cpp_noexcept_function_type`
  等）在 C++14 模式下不定义；
- `<optional>/<string_view>/<variant>/<filesystem>/<barrier>/<span>/
  <ranges>` 等头文件在 C++14 模式下 `__has_include` 语义/特性宏不满足
  pybind11 的 `#if defined(PYBIND11_CPP20)` 守卫；
→ 测试源码守卫不成立 → `m.attr("defined_...")` 未设置 → pytest skipif 触发。

实测：`clang++ -std=c++20` 下这些头文件 **全部 AVAILABLE**（逐个编译探针
验证），`__cpp_noexcept_function_type`/`__cpp_inline_variables` 在
c++17/c++20 下均为 YES。→ 根因是**构建标准**，不是平台头文件缺口。

## 方案（rec_approach: test-build-standard-escalation）
1. 遇到上游测试大量 `no <头文件>/feature not available` skip 时，先检查
   测试模块 flags.make 是否设定了 C++ 标准；未设定 → 用
   `-DCMAKE_CXX_STANDARD=20 -DCMAKE_CXX_STANDARD_REQUIRED=ON` 重建测试模块。
2. 重建后重跑套件；消除的项转实跑通过，剩项才逐项核证真实平台条件。
3. 真正不可消除的三类（本库实测）：
   - `<experimental/optional>`：libc++ 不提供该实验头（GCC 传统头）；
   - `__cpp_nontype_template_args`：clang 15 未定义（实测 VAL=0），
     C++20 NTTP 字符串字面量测试无法启用；
   - `<ranges>` 相关测试：上游显式排除 clang<16
     （test_pytypes.cpp 守卫引用 llvm/llvm-project#52696）。

## 验证（本任务真实日志）
- r01：flags.make 无 -std → 51 skipped / 1151 passed（95.44%）。
- r02：`-DCMAKE_CXX_STANDARD=20` 重建 12 个扩展模块 + Eigen3 3.4.1 +
  numpy 2.5.3/scipy 1.18.1 + boost 1.84.0 + `-DPYBIND11_HANDLE_REF_DEBUG`
  → **21 skipped / 1324 passed（98.15%，可执行集合 99.70%）**，51→21 消除
  30 项（其中 C++17/20 特性类约 28 项）。
- 日志：`$HOME/.oh-runner/logs/pybind11-3.1.0-r02-pc1-3-20260920T184000Z/`
  （pytest_final.log、skip_elimination_report.log、double_caliber_stats.log）。

## 适用边界与反例
- 适用：OHOS clang15 上以默认标准（gnu++14）构建上游 CMake 测试套件的
  C++ 库；pytest/CTest/GTest 特性宏驱动 skip 的套件。
- 反例：重建后仍 skip 且经逐项核证为真实平台条件（experimental 头缺失、
  clang15 特性宏未定义、clang<16 上游排除、Python 版本门槛 3.14+ 等）的项，
  不得强行消除，按逐项留证规则处理。

## 查重差异（vs 既有草稿，七轴）
vs DRAFT-ohos-clang15-libcxx-cxx20-capability-gaps（既有，描述 clang15
libc++ C++20 头能力缺口）：
- exact_duplicate: false（对象不同：该草稿讲库编译期头缺口，本条讲测试模块构建标准）
- causal_duplicate: false（根因不同：标准未设 vs 头缺失；实测头文件在 c++20 下可用）
- trigger_overlap: true（同为 C++17/20 特性在 clang15 上不可用的表象）
- solution_overlap: false（方案不同：本条为重建测试模块提升标准，该草稿为平台缺口头处理）
- combination_novelty: true（"skip 根因=构建标准"的分类与"先重建再核证"流程为新组合）
- boundary_novelty: true（修正既有"头文件缺口"叙述：多数头在 c++20 可用，真正缺口仅三类）
- test_migration_novelty: false
vs DRAFT-pybind11-3.1.0-langpreflight-cpp（r01 本库草稿）：领域不同（语言预检 vs 测试构建），
无重叠。
结论：部分重叠但新增差异（构建标准根因 + 先重建再核证流程）已由本轮真实日志验证且可跨库复用
→ new_draft（本 .kv/.md 同 stem 配对）。

## 关系
- similar_to: DRAFT-ohos-clang15-libcxx-cxx20-capability-gaps,
  DRAFT-daw-header-libraries-clang15-frontend-ice-cxx20-weverything,
  DRAFT-pybind11-3.1.0-langpreflight-cpp
- caused_by: 测试模块按编译器默认标准（gnu++14）编译，未显式设置 CMAKE_CXX_STANDARD
- prerequisite_of: （无）
- conflicts_with: （无；与"头缺口"草稿互补：本条处理可消除部分，该草稿覆盖真实缺口头）
