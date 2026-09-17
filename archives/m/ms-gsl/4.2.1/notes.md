# ms-gsl 4.2.1 HarmonyOS 适配笔记

## 适配摘要

- 纯 header-only（`package_type = "header-library"`，`package_id()` 清空 settings），上游公开头文件零改动。
- 上游 CMake 安装导出官方 `Microsoft.GSL::GSL` 目标，配方直接复用（`package_info()` 设置 `cmake_file_name`/`cmake_target_name`）。
- 上游测试在 configure 期用 `ExternalProject_Add` 从 GitHub `git clone` GoogleTest；补丁 `0001-use-conan-gtest.patch` 改为 `find_package(GTest CONFIG REQUIRED)` 并链接 Conan `gtest/1.17.0` 提供的 `GTest::gtest_main`（`test_requires("gtest/1.17.0")` + `CMakeDeps` + `GTest_DIR` 注入）。**测试断言一字未改，未删任何用例。**
- OHOS libc 的 `stdio.h` 递归展开 `stderr` 宏，而上游测试开 `-Weverything ... -Werror`；补丁**仅对测试目标**追加 `-Wno-disabled-macro-expansion`。
- E092：`generate()` 对 OHOS 传 `CMAKE_SYSTEM_NAME=Linux`、`CMAKE_SYSTEM_PROCESSOR=aarch64`；OHOS 的 pthread 在 libc 内，置 `CMAKE_HAVE_LIBC_PTHREAD=1` 避免 CMake 误选不存在的 `-lpthreads`。
- 构建配置：`GSL_INSTALL=ON`、`GSL_TEST=ON`、`GSL_CXX_STANDARD=17`（上游本体要求 C++14，17 沿用同上游既有配方 `archives/c/cpp-gsl/4.2.2` 的构型）。

## 上游测试口径（五维账本）

| 维度 | 数量 | 证据 |
|---|---|---|
| N_static（上游静态声明） | 96 条 `TEST()` + 1 个独立程序 = 97 | 逐文件清点：algorithm 4 / assertion 2 / at 5 / byte 4 / notnull 12 / owner 1 / pointers 2 / span_compatibility 1 / span_ext 12 / span 39 / strict_notnull 4 / utils 10；`tests/no_exception_ensure_tests.cpp` 无 `TEST()`，是自带 `main()` 的独立自检程序 |
| N_registered（构建系统注册） | 2 个可执行目标 / ctest 注册 2 项 | `tests/CMakeLists.txt`：`add_executable(gsl_tests …)` + `add_test`、`add_executable(gsl_noexcept_tests …)` + `add_test` |
| N_executed（实际执行） | 89 = 88 条 GoogleTest 用例 + 1 个 `gsl_noexcept_tests` | `ctest --test-dir <build> --output-on-failure -V`：`1/2 Test #1: gsl_tests ... Passed 14.46 sec`、`2/2 Test #2: gsl_noexcept_tests ... Passed 0.03 sec`、`100% tests passed, 0 tests failed out of 2` |
| 未实例化（不计入通过，也不从分母删除） | 8 条 `TEST()` | 7 条受 `#if defined(__cpp_lib_span) && __cpp_lib_span >= 202002L`（含 `&& defined(__cpp_lib_ranges)` 变体）保护，需 C++20 `std::span`/ranges——本构型按 C++17 构建；1 条受 `#ifdef CONFIRM_COMPILATION_ERRORS` 保护的负编译样例（`algorithm_tests.cpp: TEST(algorithm_tests, incompatible_type)`）。其余条件块（`__cplusplus >= 201703L` 3 条、`#ifndef GSL_KERNEL_MODE` 2 条）在本构型下满足，已实例化 |
| N_consumer（消费者测试） | 1 个程序 / 9 组断言 | `test_package/test_package.cpp`：`gsl::span`（含 `subspan`）/`gsl::at`/`gsl::not_null`/`gsl::narrow`/`narrow_cast`/`gsl::finally`，每失败一组返回独立非零码；`conan create` 日志含 `Linking CXX executable test_package` 与 `RUN: ./test_package` → `ms-gsl test_package passed` |

## 验证摘要

- `conan-verify`：PASS（G0–G4 + L2/L4/L5）
- 上游测试：**89/89 通过**（ctest 0 failed）
- 消费者测试：**1/1 通过**
- W3 本地 CI 模拟（`finish` step [5/10]）：PASS
- 分支基线：`feat/ms-gsl-4.2.1` 从 `upstream/main`(576aa6e6a1) 切出；本次任务提交见该分支 head（PR 中可查）

## 路径判断

**纯路径 A。** 理由：本仓库已有同一上游的先例配方（`archives/c/cpp-gsl/4.2.2`，含同型 gtest 替换补丁）与同类配方（`archives/a/atracdenc/0.2.3`），`recipe-search ms-gsl -b cmake` 的首位命中即为 cpp-gsl；本次没有产生可跨仓库复用的新知识（补丁模式、OHOS 告警处理均已在库），故不申报路径 B。

## 其他

- 本仓库既有 `archives/c/cpp-gsl/4.2.2` 与 `archives/m/msgsl/4.0.0` 来自同一上游项目；本任务包名/版本（ms-gsl 4.2.1）是平台任务指定，未改动既有目录。
---

**编译结束**: 2026-09-16 01:23
**最终状态**: built
