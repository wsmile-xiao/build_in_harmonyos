# libhwy_test

## 简介

Google Highway 1.3.0 上游源码树内的**测试支持库**（上游 CMake 目标 `hwy_test`，
产物 `libhwy_test.a` / `libhwy_test.so`）：

- `hwy/tests/test_util.{h,cc}` + `test_util-inl.h`：Highway 官方测试套件共用的
  测试工具（`RandomState`、`RandomFiniteValue`、`TypeName`、`AssertEqual`
  系列、`ForAllTypes` / `ForPartialVectors` 等向量长度枚举器）；
- `hwy/tests/hwy_gtest.h`：**standalone GTest 兼容运行器**（`HWY_TEST_STANDALONE=1`
  时不需要 googletest，自带 `TEST` / `HWY_TEST_MAIN` / `--gtest_filter` 实现）；
- `libhwy-test.pc`：上游自带的 pkg-config 模块。

本包与 `archives/l/libhwy/1.3.0` 同源同版本（同一上游 tarball
`google/highway` 1.3.0，sha256 `07b3c1ba…`），是同一 tarball 的不同子库打包面。

## OHOS 适配

- **版本**：1.3.0
- **构建**：CMake；`CMAKE_SYSTEM_NAME=Linux` 选中 Linux/NEON 分支；
  `CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY` 绕过部分 worker 缺 libxml2 的探测链接问题
- **交付面**：`libhwy_test` + `hwy/tests/*.h` + `libhwy-test.pc`，以及 hwy_test 以
  PUBLIC 方式依赖的 `hwy` 核心库与头文件（消费者缺后者无法编译/链接）
- **依赖**：零外部依赖；仅链接系统库 `m`、`pthread`
- **测试**：`HWY_TEST_STANDALONE=ON`（不下载 googletest）。交付面内的上游用例
  `hwy/tests/test_util_test.cc` 随 `conan create` 真机执行；test_package 做 15 项
  消费者检查。同一 tarball 其余 SIMD 用例的测试对象是 hwy / hwy_contrib，不属本包
  交付面，按 NOT_RUN 记账（台账见 `1.3.0/notes.md`）

## 依赖

无。
