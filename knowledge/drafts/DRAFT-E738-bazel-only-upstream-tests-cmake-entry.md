# DRAFT-E738-bazel-only-upstream-tests-cmake-entry

> Draft（待审核 promote）｜对应: `knowledge/drafts/DRAFT-E738-bazel-only-upstream-tests-cmake-entry.kv`

**标题**：上游 tests/ 只接 Bazel 时，用配方生成的 CMake 子工程补层 1 测试入口（conan gtest 钩子与导出契约两坑）

**阶段: `build|testing` · 触发: `conan|cmake|ctest` · 类别: `testing, conan-recipe, build-system, portability` · 严重级: `2`**

## 错误签名（error_signature）

```text
|-
  'gtest/gtest.h' file not found|
  Could not find a package configuration file provided by "gtest"|
  undefined reference to `RUN_ALL_TESTS`|
  AttributeError.*has no attribute 'test_requires'|
  L1c: No upstream make check/ctest in log|
  upstream tests are only wired via Bazel
```

## 根因（root_cause）

|-
  tinyalsa v2.0.0 的 tests/ 是 6 个 gtest（C++17）用例，唯一的构建接线在 Bazel 的
  `BUILD`（`cc_test` + `@googletest//:gtest_main`）；CMakeLists.txt / meson.build /
  Makefile 三处都没有 test/check 目标，`ctest` 与 `make check` 全都无从谈起。要满足
  「层 1：上游官方测试在 build() 里跑」（docs/TEST_QUALITY_SPEC.md §3），只能由配方
  自己补入口。补的过程中有三个互相独立的坑，任一都会让测试段整体失效：
  1. Conan 2.x 只调用 `requirements()` 与 `build_requirements()` 两个钩子，把 gtest
     写成名为 `test_requirements()` 的方法**永远不会被执行**（依赖不进图、CMakeDeps
     不生成 gtest-config.cmake），且不报错；正确写法是在 `build_requirements()` 里
     调用 conan 注入的 `self.test_requires("gtest/1.17.0")`（traits: headers/libs=True、
     visible=False、test=True，不传染下游）。
  2. conan gtest 1.17.0 的 CMakeDeps 只声明 `gtest::gtest`，`gtest_LIBS_RELEASE` 只有
     `gtest`，**不导出 gtest_main**（上游 BUILD 是链 `@googletest//:gtest_main` 的），
     直接 add_executable 会 undefined reference to main。
  3. 测试子工程必须复用 `self.generators_folder/conan_toolchain.cmake`（否则拿不到
     CMAKE_PREFIX_PATH/CMAKE_CXX_STANDARD=17/libc++），并把被测产物路径
     `libtinyalsa.so` 作为链接输入，保证测的是本次构建的库而不是别的副本。

## 方案（rec_approach）

recipe-generated-cmake-test-subproject

## 关键词

tinyalsa, Bazel, cc_test, googletest, gtest, gtest_main, test_requires, build_requirements, ctest, CMakeDeps, CMake 子工程, 层 1 上游测试, 上游测试入口, TEST_QUALITY_SPEC, gtest_list_tests, 参数化用例, INSTANTIATE_TEST_SUITE_P

## 来源

本条目取自 `knowledge/drafts/DRAFT-E738-bazel-only-upstream-tests-cmake-entry.kv`；promote 后对应 `knowledge/doc/E###.md`。
