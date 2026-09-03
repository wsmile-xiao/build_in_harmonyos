# tinyply 3.0 — HarmonyOS PC 适配记录

## 库概述

tinyply 是单头文件、零依赖（仅 C++ STL）的 PLY 网格文件格式 C++ 实现，
公共领域（Unlicense）。虽然以单头文件形式分发，上游仍提供独立编译单元
`source/tinyply.cpp`；本配方将其编译为 `libtinyply.a` 静态库，产物为
`lib/libtinyply.a` + `include/tinyply.h`。

- 上游：https://github.com/ddiakopoulos/tinyply（tag `3.0`，无 v 前缀）
- 源码 sha256：`928f95f36c9dfcadffe6c1c349be8e7382e16c5faab9ae72f2e4f368a11a8bd4`
- 零依赖：`ci/scripts/preflight_check.sh tinyply/3.0` 预检通过
- 零补丁：未修改上游任何源码或测试

## 构建要点

- 编译器取自 `tools.build:compiler_executables`（R33）；平台判断用
  `settings.os in (...)`（R32）。
- `build()`：clang++ `-std=c++17 -O2` 编译 `tinyply.cpp` → `llvm-ar rcs`
  打包 `libtinyply.a`（与上游 CMake 默认 STATIC 一致，CMakeLists 要求 C++17）。

## 上游测试现状与执行口径

- `source/tests.cpp`：doctest 套件，**31 个 TEST_CASE**（静态计数）。
  其中 12 个用例读取 `../assets/validate/{valid,invalid}/` 夹具；上游在
  tests.cpp 头部注释中明确这些资产因来源与版权原因**不再分发**（仓库仅含
  `assets/` 下 6 个示例文件）。上游自有 CI（appveyor.yml）仅执行
  `cmake --build`，从不构建/运行测试（`BUILD_TESTS` 默认 false）。
- `source/Makefile` 的 `all` 目标：`tinyply.cpp + example.cpp` 编译为
  `tinyply-core`；example 是自包含的写读回环（写 example_cube ascii+binary，
  再读回）。
- 本配方 `build()`（run_upstream_tests=True）真实执行：
  1. example 回环（上游 Makefile all 口径）→ exit 0；
  2. doctest 套件以官方 `--test-case-exclude` 排除恰好 12 个资产依赖用例后
     执行其余 19 个 → `19 executed, 19 passed, 0 failed`。
  排除清单逐条对应失败用例（含通配前缀防误伤：曾验证 `*int128*` 会误伤
  可通过的 `header.invalid-face-size-type-int128.ply` 用例，故用
  `check that int128*` 精确前缀；含逗号的用例名不能作精确匹配项，
  因 doctest 以逗号分隔过滤器）。
- 排除只发生在运行参数层面，未修改任何测试源码。
- 统一申报口径：上游源码静态总量为 32（31 个 doctest TEST_CASE + 1 个 example 检查），实际执行 20 项（19 个 doctest + 1 个 example），12 个缺失夹具用例跳过；通过率按 20/32 记录。

## test_package（鸿蒙特有）

`test.cpp` 消费者侧 10 个 CHECK：ascii/binary 双格式写（`add_properties_to_element`
+ `write`）、`parse_header`/`is_binary_file`/`get_elements` 头信息、
`request_properties_from_element`、`read()` 计数与数值往返一致、
face 列表元素缓冲大小、非法头拒绝。实测 10/10 通过。

## OHOS 适配要点

- test_package 的 CMakeToolchain 对 OHOS 注入 `CMAKE_SYSTEM_NAME=Linux`
  映射（知识图谱 E092），并设 `CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY`。
- 消费端 `find_package(tinyply REQUIRED)` + `tinyply::tinyply`
  （cmake_target_name 属性；上游 CMake 导出无命名空间目标 `tinyply`）。

## 验证

```
conan create archives/t/tinyply/3.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

**编译结束**: 2026-09-02 04:10 / **最终状态**: built
