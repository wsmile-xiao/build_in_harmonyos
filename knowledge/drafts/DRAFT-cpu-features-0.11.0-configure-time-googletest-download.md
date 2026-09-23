# DRAFT-cpu-features-0.11.0-configure-time-googletest-download

> Contributor: 2301_76770579 | Status: Draft | Updated: 2026-09-09
> Source: cpu_features 0.11.0 HarmonyOS PC 适配（configure 期联网下载 googletest → Conan gtest）

## 现象

cpu_features 0.11.0 在 `-DBUILD_TESTING=ON` 时 configure 直接失败：
`CMake step for googletest failed`。原因是上游 CMakeLists.txt 在不存在
gtest/gmock_main 目标时，用 `execute_process` 在 **configure 期**跑一个子
CMake 工程（cmake/googletest.CMakeLists.txt.in）联网下载 googletest，
构建沙箱无网络 → FATAL_ERROR。

## 根因

- google 系老项目的经典模式：googletest 不经包管理器，configure 期现场下载。
- 目标判定条件是 `NOT TARGET gtest OR NOT TARGET gmock_main`（裸目标名），
  而 Conan gtest 提供的是 `GTest::gtest`/`GTest::gmock_main` 命名空间目标，
  即使依赖就位也会被判定为"不存在"而重走下载分支。

## 解决方案

1. patch（patches/0001-use-conan-gtest.patch）删掉整个下载块，换
   `find_package(GTest REQUIRED)`；
2. test/CMakeLists.txt 的 `link_libraries(gtest gmock_main)` 换成
   `link_libraries(GTest::gmock_main GTest::gtest)`；
3. conanfile `test_requires("gtest/1.17.0#...")`（atracdenc 已验证先例），
   `tc.cache_variables["BUILD_TESTING"]="ON"`，build() 内
   `cmake.ctest(cli_args=["--output-on-failure"])` 全量实跑；
4. aarch64 适用 4 个测试二进制共 30 个 TEST 用例（其余 9 个架构专属二进制
   由上游 CMake 按 CMAKE_SYSTEM_PROCESSOR 自行门控，非适配裁剪）。

## 禁止策略

- 不得 `-DBUILD_TESTING=OFF` 绕过下载——等于砍掉 30 个上游用例，rule4 少报。
- 不得保留裸 `link_libraries(gtest gmock_main)`——Conan 无此目标。
- 不得用 ExternalProject/FetchContent 任何形式的联网拉取——沙箱必失败。

## 适用范围

所有 configure 期 execute_process/FetchContent 联网下载 googletest 的
CMake 项目（google 系老项目高发）：patch 换 find_package + GTest:: 目标 +
Conan test_requires。
