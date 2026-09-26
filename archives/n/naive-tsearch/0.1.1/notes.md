# naive-tsearch 0.1.1 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMakeLists ≥3.10，零补丁）
- 编译日期: 2026-09-25
- 编译器: clang 15.0.4 / clang++（OHOS aarch64，profile `ci/conan/profiles/ohos-aarch64`）
- 状态: built

## 编译步骤

原生（非 Conan，对照轮）：
```bash
cmake -S "$BUILD_SRC_DIR" -B <build> -DCMAKE_BUILD_TYPE=Release \
  -DNAIVE_TSEARCH_TESTS=ON -DNAIVE_TSEARCH_INSTALL=ON \
  -DBoost_USE_STATIC_LIBS=ON -DCMAKE_FIND_PACKAGE_PREFER_CONFIG=ON \
  "-DCMAKE_CXX_FLAGS=-DBOOST_TEST_NO_MAIN" \
  -DCMAKE_PREFIX_PATH=<已生成的 conan BoostConfig 目录>
cmake --build <build> -j2 && ctest --test-dir <build> --output-on-failure
```

Conan（权威链，采信轮口径）：
```bash
conan create archives/n/naive-tsearch/0.1.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  -c tools.build:jobs=2
```
配方 `build()` 内完成 configure + build + `ctest --output-on-failure -C Release`，
`conan create` 一并执行 test_package 消费者测试。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 链接期 `duplicate symbol: main`（main.cpp 与 libboost_unit_test_framework.a 的 unit_test_main.o 各一个 main） | conan CMakeDeps 给静态 Boost.Test 注入 `-DBOOST_TEST_DYN_LINK=0`；`boost/test/unit_test.hpp` 生成 main 的守卫是 `defined(BOOST_TEST_DYN_LINK)`（值不敏感）→ 定义了 BOOST_TEST_MODULE 的上游 main.cpp 生成 main；而该归档成员同时持有**必须**被调用的 `boost::unit_test::unit_test_main()` 函数，用户态 main 与归档 main 无法共存 | 测试编译注入 `-DBOOST_TEST_NO_MAIN`（`CMakeToolchain.extra_cxxflags`）：抑制用户 TU 的 main，由归档 unit_test_main.o 提供唯一 main，其未定义的 `init_unit_test()` 由 BOOST_TEST_MODULE 生成的 TU 解析（E747） |
| 2 | 原生构建 `Could NOT find Boost: missing: unit_test_framework`（明明找到了 BoostConfig.cmake） | CMake 4.x 中 FindBoost 模块已按 CMP0167 移除，未设策略时仍走模块路径；模块模式的组件定位与 CMakeDeps 生成的 BoostConfig 变量不兼容 | 原生构建加 `-DCMAKE_FIND_PACKAGE_PREFER_CONFIG=ON`；conan create 路径由 conan_toolchain.cmake 自动置位（E748） |

## 源码修改

无补丁：`patches_applied: []`，上游源码零改动（W0 三关：tag/资产 sha256 与
CCI conandata 逐字一致；ISA 专属头与 glibc printf 钩子零命中）。

## 依赖版本

- `boost/1.90.0`（`test_requires`，仅 tests/ 的 Boost.Test 链接用，不传播给消费者）——
  ohpcd 预编译二进制 `9d022ebf…` 与本仓 profile 全字段吻合（armv8/Release/clang15/
  libc++/cppstd17/OHOS 6.0，header_only=False shared=False），实测 17.2MB 直下不重建。

## 测试清点（N 取候选数法最大值，差额逐项归因）

| 口径 | 数值 | 归因 |
|---|---|---|
| CTest 框架注册数 | 3 | test_test_naive_tsearch（静态库）/ test_test_naive_tsearch_hdronly（头文件形态）/ test_test_system_tsearch（系统 tsearch 对照，OHOS musl 提供全部 6 符号故默认开启） |
| 源码 BOOST_AUTO_TEST_CASE 定义数 | 6 | test_delete.cpp 1 个 + test_walk.cpp 5 个 |
| **声明 N（case 执行数）** | **18** | 3 个可执行 × 6 case = 18（三实现对照组各自完整执行同一套 case） |
| 断言执行数（独立口径，非 N） | 177 | 3 × 59（2 + 57），实测 `59 assertions out of 59 passed` ×3 |

## 验证结果

```bash
# 原生对照轮
100% tests passed, 0 tests failed out of 3   # ctest --output-on-failure
# Conan 权威轮（conan create）
RUN: ctest --output-on-failure -C Release → 3/3 Passed（100%）
PASS: naive-tsearch consumer assertions 10/10 (static 5/5, hdronly 5/5)
# case 级直跑（--log_level=test_suite --report_level=detailed）
3 × { 6 cases; 59 assertions out of 59 passed }，rc=0×3
```

## 注意事项

- 上游 tests/ 需要 Boost.Test；无 boost 时 CMake 的 `find_package(Boost REQUIRED)` 会在
  configure 期硬失败——依赖已实查在制品仓（W0-2）。
- 包内同时交付两种形态：`libnaive-tsearch.a` + 头文件形态三件（search.h/tsearch_hdronly.h/
  tsearch.c.inc），test_package 对两形态各跑 5 项断言。
- 系统对照组（test_system_tsearch）依赖 libc 提供 tsearch/tfind/tdelete/twalk/tdestroy——
  设备与 CI worker 均为 musl，`tdestroy` 可链接（本机探针实证），该用例非鸿蒙特有豁免。
