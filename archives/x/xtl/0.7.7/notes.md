# xtl 0.7.7 适配笔记

## 编译环境

- 构建系统: cmake
- 评估日期: 2026-07-26
- 编译器: clang 15.0.4
- 状态: built（OHOS 真机 runner 单包验证通过，上游测试 24/24 通过）

## 适配依据

Morpheus 2.4.1 上游 `3rdparty/xtensor/CMakeLists.txt` 指定 `XTL_GIT_TAG 0.7.7`。该版本是 header-only CMake INTERFACE 库，源码无需补丁。

## Conan 配方要点

- `package_type = "header-library"`
- Conan 包构建阶段关闭上游测试：`BUILD_TESTS=OFF`、`DOWNLOAD_GTEST=OFF`
- 按 E191 设置 `CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY`
- `package_info()` 导出 `cmake_file_name=xtl`、`cmake_target_name=xtl`

## 验证设计

`test_package` 编译并运行 C++ 消费者程序，覆盖：

- `xtl::optional()` 和 `xoptional::value()/has_value()/value_or()`
- `xtl::variant` 与 `xtl::xget`
- CMake 消费路径 `find_package(xtl REQUIRED)` + `target_link_libraries(... xtl)`

## OHOS 真机验证

- 时间: 2026-07-26 18:09 CST
- runner run_dir: `/storage/Users/currentUser/ohos-test-runs/codex-xtl-xtl-xtl-0.7.7-20260726-validate-workflow-conan-r3-20260726-180833-63258`
- 命令: `zsh ci/conan/build_and_test.sh archives/x/xtl/0.7.7`
- 结果: `Total: 1`, `Success: 1`, `Failed: 0`
- 门禁: `L0=pass`, `L1=pass`, `L2=skip(no bin/ dir)`, `L4=pass(no patches)`, `L5=warn(no bin/lib content; header-only package)`
- `test_package` 编译并运行 `./test_xtl`，覆盖 optional、variant 和 CMake target `xtl` 消费路径。

真机环境说明：隔离 job 的 `CONAN_HOME` 需先带有 OHOS settings；当前真机不能直接执行 `$HOME/usr/local/bin/clang`/`clang++` shell wrapper，因此 runner 验证使用 `clang-15` ELF 并显式补齐 sysroot/link flags。这是 job-local 环境处理，不改变 recipe。

## 上游测试状态

release 源码包含 `test/` doctest suite；`test/CMakeLists.txt` 注册 24 个 CTest entry，包括 23 个 `test_*.cpp` 单文件测试和 1 个聚合测试 `xtest`。

- 时间: 2026-07-26 19:13 CST
- runner run_dir: `/storage/Users/currentUser/ohos-test-runs/codex-xtl-xtl-xtl-0.7.7-20260726-validate-upstream-doctest-r4-20260726-191345-32382`
- 上游源码: `/storage/Users/currentUser/ohos-users/codex-xtl/xtl-0.7.7-20260726-validate/conan-home/p/b/xtlec4d5f63f366c/b`
- 测试依赖: `doctest/2.5.2`，通过隔离 `CONAN_HOME` 中的 `conancenter` 临时获取，仅用于 upstream-only 测试
- 配置: `BUILD_TESTS=ON`、`DOWNLOAD_GTEST=OFF`、`CMAKE_POLICY_VERSION_MINIMUM=3.5`
- 结果: `UPSTREAM_TESTS_DISCOVERED=24`，`UPSTREAM_TESTS_PASSED=24`，`UPSTREAM_TESTS_FAILED=0`，`UPSTREAM_PASS_RATE=100.00%`

验证 harness 必要性与有效性：真机不能执行 `$HOME/usr/local/bin/clang` shell wrapper，也不能执行 job-local shell wrapper；最终使用真实 ELF `$HOME/usr/local/bin/clang-15` 加 sysroot/link flags。设备 CMake 4.1.2 对 upstream `test/CMakeLists.txt` 的 `cmake_minimum_required(VERSION 3.1)` 需要 `CMAKE_POLICY_VERSION_MINIMUM=3.5` 才能配置通过。上述处理均为 job-local 测试配置，不修改 xtl 源码、测试源码或 Conan recipe。
