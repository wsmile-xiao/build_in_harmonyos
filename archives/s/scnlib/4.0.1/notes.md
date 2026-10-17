# scnlib 4.0.1 适配笔记

## 基本信息

- 上游：https://github.com/eliaskosunen/scnlib（tag v4.0.1，2024-11-04）
- 类型：C++17 compiled library（`libscn`，SOVERSION 4）
- 构建系统：CMake >= 3.16
- 许可证：Apache-2.0

## 依赖分析

| 依赖 | 上游形态 | 适配决策 |
|------|---------|---------|
| fast_float | FetchContent bundled v6.1.6 | 使用仓内 conan 包 fast_float/6.1.6（精确对应上游 bundled tag），`SCN_USE_EXTERNAL_FAST_FLOAT=ON` |
| std::regex | 默认后端 std | 无需额外依赖 |
| googletest（仅测试） | FetchContent GitHub main | `SCN_USE_EXTERNAL_GTEST=ON`（上游内建开关）+ 仓内已发布 googletest/1.12.1，CMakeDeps 桥接，上游测试 26/26 全过 |

## 关键决策与理由

### 1. fast_float 外部化 + find_package 命名 patch

上游 `cmake/dependencies.cmake` 的 external 分支写死 `find_package(FastFloat CONFIG REQUIRED)`，
期望上游 fast_float 手写的 `FastFloatConfig.cmake`。Conan CMakeDeps 生成的是
`fast_float-config.cmake`（小写包名，`find_package(fast_float)`），target 为
`fast_float::fast_float`。patch 0001 改为先试小写（Conan 路径）再回退大写（上游路径），
`SCN_FAST_FLOAT_TARGET` 按 target 实际存在性选择。

不采用 `SCN_DISABLE_FAST_FLOAT=ON` 的原因：那会要求 std::from_chars 浮点支持，
OHOS libc++（NDK r26/clang 15）的 `std::from_chars(double)` 支持不完整，风险更高。

### 2. xlocale 无需 patch

`src/scn/impl.cpp` 的 `SCN_XLOCALE` 检测链：
`__has_include(<xlocale.h>)`（OHOS musl 无此头）→ `_MSC_VER`（否）→
`__GLIBC__`（musl 不定义，跳过 glibc 分支）→ FreeBSD（否）→
最终 `SCN_XLOCALE_OTHER`：`std::strtof/std::strtod/std::strtold` +
`set_clocale_classic_guard`，纯 std 路径，OHOS libc++ 可用。

### 3. 测试策略

- 上游 unittests（scn_tests/scn_impl_tests 等）：`SCN_USE_EXTERNAL_GTEST=ON` + 仓内 googletest/1.12.1
  （上游对 gtest 无版本约束，`find_package(GTest CONFIG REQUIRED)` 无版本检查，本地实测 26/26 全过）。
  googletest 桥接零 patch：上游 install 导出目标名即 `GTest::gtest_main`/`GTest::gmock_main`，
  与 Conan CMakeDeps 生成的完全一致
- 上游默认形态（SCN_CI=ON）注册的 CTest 目标：scn_tests、scn_impl_tests、scn_stdin_test（Python runner）、
  scn_examples_test（Python runner）+ 22 个 compile-fail 测试（8 个 regex 相关）。
  compile-fail 测试需 icm_build_failure_testing 模块（tests/unittests/compilefail_tests/）
- **上游测试实测结果（OHOS aarch64，clang 15，libc++，googletest/1.12.1）**：
  26/26 CTest 目标全部通过——scn_tests 336 断言 + scn_impl_tests 2275 断言 +
  scn_stdin_test 1 断言 + scn_examples_test 1 目标 + 22 compile-fail；build() 中 `ctest --output-on-failure` 执行
- OHOS 运行时要点：musl ld.so 需 `LD_LIBRARY_PATH=/system/lib64` 解析 `libc++_shared.so`
  （与 test_package 同一先例）；compile-fail 测试写临时文件需 `TMPDIR` 指向可写构建目录（/tmp 只读 E002）
- test_package 消费者测试 9 组断言：int/多值混合/float(fast_float 路径)/string/
  空白跳过+负数/错误处理(invalid_scanned_value)/xchar 宽字符/vector range/scan_int

## 构建验证

- 本地 conan create：OHOS aarch64（clang 15, libc++, C++17）通过，上游测试 25/25 全过
- test_package 二进制在设备/模拟环境链接执行通过
