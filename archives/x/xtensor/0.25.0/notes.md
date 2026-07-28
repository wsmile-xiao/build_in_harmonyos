# xtensor 0.25.0 适配笔记

## 编译环境

- 构建系统: cmake
- 评估日期: 2026-07-27
- 编译器: clang/clang++
- 状态: built（OHOS Conan `test_package` 与 release 源码上游测试通过）

## 适配依据

Morpheus 2.4.1 上游 `3rdparty/xtensor/CMakeLists.txt` 指定 `XTENSOR_GIT_TAG 0.25.0`。该目录默认通过 CMake `FetchContent` 联网拉取 xtensor 栈；按仓库 R36 的依赖优先原则和可复现构建要求，应先将 xtensor 栈作为 Conan 依赖显式适配。

## Conan 配方要点

- `package_type = "header-library"`
- 依赖 `xtl/0.7.7`、`xsimd/13.2.0`
- `XTENSOR_USE_XSIMD=ON`，匹配 Morpheus 对 `XTENSOR_USE_XSIMD` 的使用
- 禁用上游测试/benchmark/GTest 下载
- 按 E191 设置 `CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY`
- `package_info()` 导出 `cmake_file_name=xtensor`、`cmake_target_name=xtensor`
- 补丁 `0001-align-xsimd-required-version.patch` 将上游 CMake 安装配置中的 `xsimd_REQUIRED_VERSION` 从 11.0.0 对齐为 13.2.0，避免 `XTENSOR_USE_XSIMD=ON` 时生成的 `xtensorConfig.cmake` 与 Morpheus 依赖链不一致

## 验证设计

`test_package` 编译并运行 C++ 消费者程序，覆盖：

- `xt::xarray<double>` 二维数组构造
- xtensor 懒表达式加法
- `xt::sum()` 归约
- CMake 消费路径 `find_package(xtl/xsimd/xtensor REQUIRED)` + `target_link_libraries(... xtensor)`

## OHOS 验证结果

- Conan run_dir: `/storage/Users/currentUser/ohos-test-runs/codex-a-xtensor-xtensor-0.25.0-20260727-r1-conan-r3-patched-20260727-203012-33551`
- 结果: `L0_RESULT=pass`, `L1_RESULT=pass`, `L2_RESULT=skip`（header-only 无 `bin/`）, `L4_RESULT=pass`, `L5_RESULT=warn`（无 `bin/`/`lib/` 制品）
- `test_package` 在 OHOS aarch64 上编译并执行 `./test_xtensor` 通过；破坏性负测确认测试依赖实际 `xtensor` 头文件

## 上游测试

- 上游 release source: Conan patch 后的 `xtensor/0.25.0` build source
- run_dir: `/storage/Users/currentUser/ohos-test-runs/codex-a-xtensor-xtensor-upstream-tests-0.25.0-r5-nlohmann-include-20260727-210305-56202`
- 配置: `BUILD_TESTS=ON`, `XTENSOR_USE_XSIMD=ON`, `CPP17=ON`, `BUILD_BENCHMARK=OFF`
- 测试依赖: job-local `doctest` CMake config；ConanCenter `nlohmann_json/3.11.3` 仅用于上游测试，覆盖 `test_xjson`/`test_xmime`/`test_xexpression_holder`
- 结果: `ctest` 80/80 passed, `100% tests passed, 0 tests failed out of 80`
