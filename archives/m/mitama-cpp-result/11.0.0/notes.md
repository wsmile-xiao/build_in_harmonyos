# mitama-cpp-result 11.0.0 适配笔记（HarmonyOS PC · header-only）

## 上游核实（官方真实信息）

- 官方仓库：https://github.com/LoliGothick/mitama-cpp-result
- 精确 tag：v11.0.0
- 源码 URL：https://github.com/LoliGothick/mitama-cpp-result/archive/refs/tags/v11.0.0.tar.gz
- SHA256：`fdfe81098660e7365e79760616231eefdd42dd7760970c0e7ea4c6bacce46440`
  （经 codeload.github.com 实测下载并 sha256sum 校验，与 release tarball 一致）
- License：MIT（`LICENSE`，Copyright (c) 2018 Cranberries）

## 构建系统 / 库特性

- **构建系统**：CMake（`cmake_minimum_required(VERSION 3.8)`）
- **是否 header-only**：是。上游 `CMakeLists.txt` 用
  `add_library(${PROJECT_NAME} INTERFACE)` + `target_compile_features(... cxx_std_20)`，
  install 只装 `include/*.hpp`（`FILES_MATCHING PATTERN "*.hpp"`）与 cmake config
  （`share/mitama-cpp-result/`），**无 .so / .a / .bin**。
- **C++ 标准**：C++20（上游用 concepts、`consteval`、`requires` 子句）
- **安装产物**：`include/mitama/**/*.hpp` + `share/mitama-cpp-result/mitama-cpp-result-config.cmake`
  （+ `-config-version.cmake` + `mitama-cpp-result-targets.cmake`），`licenses/LICENSE`

## fmt 依赖

- 上游头文件 `#include`：`<fmt/core.h>`、`<fmt/format.h>`、`<fmt/ostream.h>`、
  `<fmt/ranges.h>`、`<fmt/std.h>`（`result.hpp:13` 含 `<fmt/std.h>`，要求 fmt >= 9.0）。
- 上游 `test/CMakeLists.txt`：`find_package(fmt 9.0.0 CONFIG REQUIRED)`，链接
  `fmt::fmt-header-only`。
- **本仓库已发布 fmt/12.2.0**（见 archives/f/fmt/12.2.0，含 `<fmt/std.h>`、
  `fmt::ostream_formatter`），满足上游要求。
- 本 recipe `self.requires("fmt/12.2.0")`，**不下载/内置第二份 fmt**。

## 其他第三方依赖

- 无。运行时仅 fmt；上游测试用 Catch2（git submodule，非运行时依赖）。

## 上游正式测试目录 / 注册测试数量

- **正式测试目录**：`test/`（3 个测试源文件 + 辅助头）
  - `test/result_tests.cpp`、`test/maybe_tests.cpp`、`test/anyhow_tests.cpp`
  - `test/TestClass.hpp`、`test/special_member_tests.hpp`（辅助）
- **测试框架**：Catch2 v2.13.8（git submodule，`.gitmodules` 声明分支 `v2.13.8`）
- **上游 CMake 注册的可执行测试**：3（`add_test` 每个 TEST_NAME 一个）
- **源码 TEST_CASE 宏数**：100（result=52, maybe=42, anyhow=6）
- **OHOS 实测运行结果**（Catch2 生成器展开后）：108 test cases, 145 assertions
  - `result_tests`：60 test cases / 89 assertions — PASS
  - `maybe_tests`：42 test cases / 43 assertions — PASS
  - `anyhow_tests`：6 test cases / 13 assertions — PASS
  - **TOTAL=108 PASS=108 FAIL=0 SKIP=0**

## 关键适配

- **0 patch**：fmt/12.2.0 已提供 `<fmt/std.h>`，上游 `result.hpp:13` 的 include 原样有效，
  无需裁剪（旧版 fmt/8.1.1 曾需补丁删该行，已废弃）。
- `package_type = "header-library"`，`no_copy_source = True`
- `package()`：`copy(*.hpp, include → include)` + `copy(LICENSE → licenses)`
- `cpp_info`：`bindirs=[]`、`libdirs=[]`、`includedirs=["include"]`；
  `components["mitama"].requires = ["fmt::fmt"]` 传递 fmt 给消费方
- cmake 目标名 `mitama-cpp-result::mitama-cpp-result`（对齐上游 EXPORT NAMESPACE）
- 无 HarmonyOS.cmake hack：header-only 不编译二进制，无需 `CMAKE_SYSTEM_NAME` 守卫；
  test_package 的 CMakeToolchain 仍带 os=OHOS 守卫以对齐 fmt/12.2.0 shared 库链接

## API（11.0.0 实际头文件确认）

核心类型 `mitama::result<T, E>`，位于 `include/mitama/result/result.hpp`（2183 行）。
- 构造：`success_t<T>{v}` / `failure_t<E>{e}`（`factory/success.hpp`、`factory/failure.hpp`）
- 谓词：`.is_ok()` / `.is_err()`
- 取值：`.unwrap()` / `.unwrap_err()` / `.unwrap_or(d)`
- 变换：`.map(op)` / `.map_err(op)`
- 链式：`.and_then(op)`（op 返回新 result，成功分支）/ `.or_else(op)`（op 返回新 result，错误分支）

## test_package

真实 consumer 测试（非仅 include 编译测试），`find_package` + `target_link_libraries`
消费 Conan 打包产物：
- success 取值（is_ok/unwrap/unwrap_or）、error 取值（is_err/unwrap_err/unwrap_or）
- map（成功变换）、map_err（错误变换）
- and_then（成功链式，上游实证 `success(2).and_then(sq).and_then(sq)==success(16)`）
- or_else（错误链式，上游实证 `failure(3).or_else(sq)==success(9)`）
- map/and_then 在错误分支保持错误不变、or_else 在成功分支保持成功不变、分支互斥
- 共 14 个 CHECK，每个打印 PASS/FAIL，末尾打印汇总

## 源码修改

无需修改源码，0 patch。

## 依赖版本

- CMake: 4.1.2
- Clang: 15（HarmonyOS NDK，target aarch64-unknown-linux-ohos）
- 运行时依赖：fmt/12.2.0（本仓库已发布）

## 状态

built（OHOS conan create + 上游 Catch2 测试 + test_package 通过后回填）
