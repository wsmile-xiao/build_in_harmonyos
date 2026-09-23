# DRAFT: 制品仓 catch2 v2.13 合并头布局下的上游 Catch2 v3 多头测试适配

> 来源: cdt 1.4.5 HarmonyOS 适配（header-only 约束 Delaunay 三角剖分库）
> 状态: 草稿 (draft) — 与 DRAFT-cdt-1.4.5-catch2-21310-amalgamated-test-adaptation.kv 配对
> 关联: knowledge/drafts/DRAFT-kangaru-4.3.2-catch2-submodule-test-requires（互补场景）

## 问题

cdt 1.4.5 上游测试 `tests/cdt.test.cpp` include 5 个 Catch2 v3 多头路径头
（`catch2/benchmark/catch_benchmark.hpp`、`catch2/catch_template_test_macros.hpp`、
`catch2/catch_test_macros.hpp`、`catch2/generators/catch_generators.hpp`、
`catch2/matchers/catch_matchers_floating_point.hpp`），顶层 CMakeLists 在
`CDT_ENABLE_TESTING=ON` 时执行：

```cmake
find_package(Catch2 3 QUIET)        # 版本要求 ≥3
...
target_link_libraries(... Catch2::Catch2WithMain ...)
include(Catch)
catch_discover_tests(...)
```

制品仓已发布 catch2/2.13.10-r0（v2.13 合并头 `catch.hpp` 单头布局 + 4 个 reporter
头），上游标注的 catch2/3.4.0 未发布。三处真实失败：

1. **编译失败**: v3 多头 include 的头文件在 v2.13 合并头包中不存在
   （包内仅 `include/catch2/catch.hpp` 等 5 个文件）；
2. **配置失败**: `find_package(Catch2 3)` 因 2.13<3 不满足 → 下落
   `add_subdirectory(tests/Catch2)` 空目录分支；
   且 `Catch2::Catch2WithMain` 目标不存在（已发布配方只声明 `Catch2::Catch2`）；
3. **注册失败**: v2.13 包不透出 `extras/Catch.cmake` →
   `include(Catch)` 找不到文件、`catch_discover_tests` 是未知命令。

## 根因

- 制品仓 catch2/2.13.10-r0 配方只打包 `single_include/catch2/*.hpp`（合并头），
  不含 v3 多头布局；上游测试按 v3 多头 include 编写；
- v2.13 包配方未声明 Catch2WithMain 组件，也不随包透出 extras/Catch.cmake。

## 方案（三处最小补丁 + 配方两处）

补丁 0002（测试源码）——5 条 v3 多头 include 替换为合并头统一入口：

```cpp
// OHOS 适配: 制品仓已发布 catch2/2.13.10-r0（合并头 catch.hpp，含全部所需宏），
// 上游标注的 catch2/3.4.0 多头布局未发布，改用合并头统一入口。
#define CATCH_CONFIG_ENABLE_BENCHMARKING
#include <catch2/catch.hpp>
```

（v2.13 合并头实测含全部所需宏: TEST_CASE/TEMPLATE_LIST_TEST_CASE/BENCHMARK/
GENERATE/Approx/WithinAbs/SECTION；`CATCH_CONFIG_ENABLE_BENCHMARKING` 使
benchmark 宏真正定义而非被 `#if` 裁掉。）

补丁 0001（CMakeLists）——三处：

```cmake
find_package(Catch2 QUIET)                                  # 去掉版本 3
...
target_compile_definitions(${TEST_TARGET_NAME} PRIVATE CATCH_CONFIG_MAIN)  # 合并头生成 main
target_link_libraries(${TEST_TARGET_NAME} PRIVATE Catch2::Catch2 CDT::CDT)  # 无 WithMain
add_test(NAME ${TEST_TARGET_NAME} COMMAND ${TEST_TARGET_NAME}               # 替代 catch_discover_tests
         WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}/tests")
```

配方（conanfile.py）——仅测试路径 require 已发布包 + 生成 CMake config：

```python
generators = "CMakeDeps"                      # 生成 Catch2Config.cmake
def requirements(self):
    if self.options.enable_testing:
        self.requires("catch2/2.13.10-r0")
```

用例级证据采集：`catch_discover_tests` 不可用时，用二进制自带能力
`CDT-tests --list-tests`（含 `[benchmark]` 等隐藏 tag 过滤）与 `-r compact`
（"Passed all 28 test cases with 4788 assertions"）。

## 验证

```bash
conan create archives/c/cdt/1.4.5 -o cdt/*:enable_testing=True \
  -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing   # RC=0
# 上游测试: 28/28 通过, 4788 断言, 0 失败（-r compact）
# --list-tests: 28 非隐藏 + 2 隐藏 benchmark 实例
# standards_check: 编译+运行 RC=0
```

## 适用边界与反例

- **适用**: 上游测试用 Catch2 v3 多头 include / Catch2WithMain / catch_discover_tests，
  制品仓仅发布 v2.13 合并头 catch2 的库；测试用到的宏面须在 v2.13 合并头中存在
  （TEMPLATE_LIST_TEST_CASE 自 v2.13 起可用）。
- **反例**: 上游测试已用 v2.13 兼容 include（如 `catch.hpp`）→ 只需
  kangaru 式 test_requires+CMakeDeps，无需补丁；制品仓已有 catch2 v3 包 →
  直接 require v3 无需任何适配。
- **查重差异**: 与 DRAFT-kangaru-4.3.2-catch2-submodule-test-requires 为
  trigger_overlap + solution 部分重叠（均使 find_package(Catch2) 命中已发布包），
  本方案新增 include 合并头化、CATCH_CONFIG_ENABLE_BENCHMARKING、
  WithMain→CATCH_CONFIG_MAIN、catch_discover_tests→单 add_test 四个差异面；
  与 DRAFT-cmake-test-framework-fetch-to-conan-find-package 思路一致但场景不同
  （FetchContent→find_package vs 多头 include→合并头）。
