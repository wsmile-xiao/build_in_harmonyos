# itlib

**iboB's Template Libraries** — 一组与 C++ 标准库相似或扩展的小型单头文件 C++ 模板库集合（MIT）。

## 功能概述

- 35 个独立单头文件模板库（`include/itlib/*.hpp`），每个库仅依赖 C++ 标准库：
  `any`、`flat_map`、`flat_set`、`small_vector`、`static_vector`、`span`、
  `poly_span`、`expected`、`generator`（C++20）、`ufunction`、`pod_vector`、
  `pmr_allocator`（C++17）、`strutil`、`qalgorithm`、`dynamic_bitset`、
  `mem_streambuf`、`transparent_umap`、`ref_ptr` 等
- 与标准库容器相比提供更好的缓存局部性（flat_map/flat_set 底层 vector）
- C++11 起可用，部分库提供 C++14/17/20 扩展特性

## HarmonyOS PC 适配

- **header-only**：INTERFACE CMake 目标，无编译产物，无运行时依赖
- 仅依赖 C++ 标准库（OHOS libc/libc++），零补丁适配
- 上游测试经 CPM 拉取 doctest/icm/doctest-util/picobench（GitHub 依赖），
  conan create 关闭 `ITLIB_BUILD_TESTS`；上游测试在本地单独枚举运行
  （reports/upstream-test-ledger.md），消费者验证由 test_package 承担

## 依赖关系

- 编译依赖：无（仅标准库）
- 运行依赖：无

## 参考资料

- 上游仓库：https://github.com/iboB/itlib
- 文档：各头文件顶部注释