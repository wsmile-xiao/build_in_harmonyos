# biosoup 0.10.0 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMakeLists.txt 3.11+，C++11 header-only INTERFACE 库）
- 编译日期: 2026-09-18
- 编译器: clang/clang++ 15.0.4（OHOS aarch64，conan profile ohos-aarch64）
- 状态: built（conan-verify W3 全绿：G0–G4、L2、L4、L5 PASS）
- worktree: ~/qzy/GLM-50-biosoup-0.10.0（分支 feat/biosoup-0.10.0，基于 upstream/main e321afdc8c）
- CONAN_HOME: ~/tmp/ch/home-glm50-biosoup

## 编译步骤

1. `ohc-run.py init-build biosoup 0.10.0 --auto --url <官方 GitHub archive>`：下载源码（SHA256 6322791a…）、建归档骨架。
2. 编写 conanfile.py（header-library 打包 + test_requires gtest + build() 内 cmake.test() 跑上游测试）、conandata.yml（官方 URL + 真实 SHA256）、补丁 0001-cmake-test-gtest.patch、test_package 消费者测试。
3. `ohc-run.py conan-verify biosoup 0.10.0`：conan create 全链路通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | find_package(GTest) 找不到 GTestConfig.cmake | 上游用 FetchContent 构建期拉 googletest（conan 离线构建禁止）；且 conan 2 的 CMakeDeps 不为 tool_requires 生成 config（generators 目录实证无 GTest 文件） | 补丁切 find_package(GTest REQUIRED CONFIG)；test_requires(gtest/1.17.0) + generate() 手动设 GTest_DIR 指向包内 lib/cmake/GTest（abseil/20260526 先例同款） |
| 2 | gtest 1.17 头文件要求 C++14，上游锁 CXX_STANDARD 11 | 全局 CMAKE_CXX_STANDARD 11 覆盖 toolchain 的 17 | 补丁仅对测试目标 set_target_properties CXX_STANDARD 14，不动库本体 |
| 3 | 上游无 add_test/enable_testing，ctest 无用例可跑 | 上游只定义 biosoup_test 可执行，漏注册 CTest | 补丁加 enable_testing() + add_test(NAME biosoup_test COMMAND biosoup_test) |
| 4 | 消费者测试链接失败：undefined symbol biosoup::Sequence::num_objects | header-only 库的静态成员按上游惯例由使用者 TU 提供类外定义（上游 test/sequence_test.cpp:7 同款） | test_biosoup.cpp 补 `std::atomic<std::uint32_t> biosoup::Sequence::num_objects{0};` |

## 源码修改

patches/0001-cmake-test-gtest.patch（仅测试基础设施，不改库代码与消费者可见行为）：
- FetchContent(googletest 1.10) 段替换为 find_package(GTest REQUIRED CONFIG)
- 补 enable_testing() + add_test 注册
- biosoup_test 目标 CXX_STANDARD 提升至 14（gtest 1.17 要求）
- 链接目标 GTest::Main → GTest::gtest_main

## 依赖版本

- gtest/1.17.0（test_requires，仅构建期上游测试用，不入下游依赖闭包）
- 库本体零依赖（header-only）

## 验证结果

```bash
# conan create（conan-verify 内部执行，profile ohos-aarch64）
# 上游测试（ctest 驱动）：
Test project .../build/Release
1/1 Test #1: biosoup_test .....................   Passed    2.40 sec
100% tests passed, 0 tests failed out of 1
# gtest 逐用例统计：
[==========] 11 tests from 5 test suites ran. (2350 ms total)
[  PASSED  ] 11 tests.
# 消费者测试：
biosoup consumer test PASS
```

## 测试账本（五维）

- N_static（上游静态用例数）：11 —— gtest TEST 定义逐条计数：nucleic_acid_test 4 + overlap_test 1 + progress_bar_test 1 + sequence_test 1 + timer_test 4
- N_registered：1（ctest 注册 biosoup_test 可执行，承载全部 11 个 gtest 用例）
- N_executed（上游实际执行）：11 —— `[ PASSED ] 11 tests`（OHOS aarch64 真机）
- 未执行分类数：0
- N_consumer（消费者测试）：1 个程序 test_biosoup（test_package/test_biosoup.cpp），4 个断言（name/data、原子唯一 id、quality、ReverseAndComplement ACGTT→AACGT）全过

## 路径 A/B/C 判断

- 判定：纯路径 A。
- 理由：gtest 接入模式（test_requires + GTest_DIR 直指包内 config + 测试目标 C++ 提升 + ctest 注册补齐）在知识库已有 abseil/20260526 先例条目，本次为既有知识的重复应用而非新增可复用知识；无稳定错误签名增量；不满足路径 B 证据门槛。
---

**编译结束**: 2026-09-18 03:29
**最终状态**: built
