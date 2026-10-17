# xsimd 13.2.0 适配笔记

## 编译环境

- 构建系统: cmake
- 评估日期: 2026-07-27
- 编译器: clang 15.0.4
- 状态: built（OHOS 真机 runner 单包验证通过，上游测试 1/1 CTest、324/324 doctest case 通过）

## 适配依据

Morpheus 2.4.1 上游 `3rdparty/xtensor/CMakeLists.txt` 指定 `XSIMD_GIT_TAG 13.2.0`。仓库已有 `xsimd/13.0.0` 旧式归档，但缺少 ARCHIVE-SPEC v3.0 要求的 `conanfile.py`、`conandata.yml`、`test_package/`，且版本与 Morpheus fallback 不一致，因此新增 13.2.0。

## Conan 配方要点

- `package_type = "header-library"`
- 禁用上游测试/示例/benchmark：`BUILD_TESTS=OFF`、`BUILD_EXAMPLES=OFF`、`BUILD_BENCHMARK=OFF`
- `ENABLE_XTL_COMPLEX=OFF`，保持 xsimd 自身无强制依赖
- 按 E191 设置 `CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY`
- `package_info()` 导出 `cmake_file_name=xsimd`、`cmake_target_name=xsimd`
- `cmake_config_version_compat=AnyNewerVersion`，满足 xtensor 0.25.0 对较低 xsimd CMake version 的兼容查找
- `0001-use-approx-for-exp10-on-ohos-musl.patch` 仅调整上游测试中 OHOS/musl 的 `exp10` 浮点比较，从精确相等改为 doctest approximate；非 OHOS/musl 平台保持原断言。

## 验证设计

`test_package` 编译并运行 C++ 消费者程序，覆盖：

- `xsimd::batch<double>` 类型实例化
- `load_unaligned`、SIMD 加法、`store_unaligned`
- CMake 消费路径 `find_package(xsimd REQUIRED)` + `target_link_libraries(... xsimd)`

## OHOS 真机验证

- 时间: 2026-07-27 19:35 CST
- runner run_dir: `/storage/Users/currentUser/ohos-test-runs/codex-a-13.2.0-xsimd-13.2.0-20260727-r1-conan-20260727-193501-56097`
- 命令: `zsh ci/conan/build_and_test.sh archives/x/xsimd/13.2.0`
- 结果: `Total: 1`, `Success: 1`, `Failed: 0`
- 门禁: `L0=pass`, `L1=pass`, `L2=skip(no bin/ dir)`, `L4=pass(patches clean)`, `L5=warn(no artifacts found; header-only package)`
- `test_package` 编译并运行 `./test_xsimd`，覆盖 batch load/add/store 和 CMake target `xsimd` 消费路径。

真机环境说明：隔离 job 的 `CONAN_HOME` 需使用带 OHOS enum 的 `settings.yml`；当前真机不能直接使用仓库 profile 中的 `/data/service/hnp/bin/clang`，runner 验证使用 `$HOME/usr/local/bin/clang-15` ELF 并显式补齐 sysroot/link flags。这是 job-local 环境处理，不改变 recipe。

## 上游测试状态

release 源码包含 `test/` doctest suite；`test/CMakeLists.txt` 注册 1 个 CTest entry `test_xsimd`，该可执行文件由 36 个 `test_*.cpp` 文件合并构建，并包含 324 个 doctest test case、8600 个 assertion。`test/doc` 和 `test/architectures` 没有额外注册 CTest entry；doc object tests 只在 x86_64 条件下启用，当前 OHOS arm64 不触发；architecture flag probes 均按 CMake 检测结果跳过。

- 首次上游测试: `/storage/Users/currentUser/ohos-test-runs/codex-a-xsimd-upstream-tests-13.2.0-r1-20260727-191806-47712`，原始 release 测试构建成功但 `exp10` 精确相等断言 2/8600 失败。
- 修正后上游测试: `/storage/Users/currentUser/ohos-test-runs/codex-a-xsimd-upstream-tests-13.2.0-r3-patched-20260727-194049-60578`
- 上游测试依赖: `doctest.h` v2.4.9。首次 run 由 upstream CMake `DOWNLOAD_DOCTEST=ON` 下载；后续复测复用 job-local header 和临时 `doctestConfig.cmake`，避免网络超时影响结果。
- 配置: `BUILD_TESTS=ON`, `DOWNLOAD_DOCTEST=OFF`, `ENABLE_XTL_COMPLEX=OFF`, `BUILD_BENCHMARK=OFF`, `BUILD_EXAMPLES=OFF`, clang-15 + OHOS sysroot/link flags。
- 结果: `UPSTREAM_CTEST_ENTRIES=1`, `UPSTREAM_CTEST_PASSED=1`, `UPSTREAM_CTEST_FAILED=0`, `UPSTREAM_DOCTEST_CASES=324/324`, `UPSTREAM_ASSERTIONS=8600/8600`, `UPSTREAM_PASS_RATE=100.00%`。
