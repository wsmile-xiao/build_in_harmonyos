# googletest 1.17.0 适配笔记

## 概述

- 库：googletest（GoogleTest + GoogleMock，C++ 测试/模拟框架）
- 版本：1.17.0（官方 v1.17.0，2025-05-01 发布）
- 官方源：https://github.com/google/googletest
- 归档路径：archives/g/googletest/1.17.0/
- 平台任务：#7344（taskBranch=feat/googletest-1.17.0，scnlib #9694 测试依赖解锁件）

## 来源核验（2026-09-12）

- 正式标签：`v1.17.0`
- tarball：https://github.com/google/googletest/archive/refs/tags/v1.17.0.tar.gz
- sha256：`65fab701d9829d38cb77c14acdc431d2108bfdbf8979e40eb8ae567edf10b27c`
- 与仓内 gtest/1.17.0 / gtest/1.17.0.1 源码完全一致（同 sha256 逐字节核验）
- 说明：github.com 直连在本环境不可达，经 gh-proxy.com 镜像逐字节透传下载核验；
  CI 侧 build_and_test.sh 对 github.com URL 自动添加镜像 fallback。

## 包名形态说明（与 gtest/1.17.0 的关系）

- 本包是 **googletest 包名形态（上游原生名）**；仓内已有 gtest/1.17.0 / 1.17.0.1（conan
  惯用包名形态），两者源码完全一致（同 tag v1.17.0、同 sha256）。
- 目的：为下游以 `find_package(GTest)` / FetchContent(googletest) 形态消费的库提供
  googletest 原生包名依赖。平台任务 #7344，解锁 scnlib #9694 的上游测试依赖。
- CMakeDeps 桥接：recipe `cmake_file_name = "GTest"` 生成 GTestConfig.cmake，
  components 桥接 GTest::gtest / GTest::gtest_main / GTest::gmock / GTest::gmock_main
  ——与上游 CMake install 导出的 config 包名/目标名一致（googletest/1.12.1 先例同款）。
- 包本体 INSTALL_GTEST=ON 安装了上游原生 GTestConfig.cmake（lib/cmake/GTest/），
  下游 find_package(GTest CONFIG) 双保险。

## 构建要点

- 构建系统：CMake；零外部依赖；C++17
- 产出：静态库 `libgtest.a` / `libgtest_main.a` / `libgmock.a` / `libgmock_main.a`
- 关键 CMake 开关：`BUILD_GMOCK=ON`、`INSTALL_GTEST=ON`、`BUILD_SHARED_LIBS=OFF`（静态）
- 上游测试：`gtest_build_tests=ON`、`gmock_build_tests=ON`
- 参考配方：archives/g/gtest/1.17.0.1/conanfile.py（同源码既有配方，改包名）
  + archives/g/googletest/1.12.1/conanfile.py（googletest 包名形态先例）

## 上游测试实测（N 注册口径）

上游 CMake 注册测试目标（add_test）**实测 ctest -N = 63**：

- googletest 侧 45 = 24 cxx_test + 3 cxx_test_with_flags（ex_nocatch/ex_catch/no_rtti）
  + 18 py_test（Python3 Interpreter 找到后注册）
- googlemock 侧 18 = 15 cxx_test + 1 gmock_stress_test（GTEST_HAS_PTHREAD）+ 2
  cxx_test_with_flags（no_exception/no_rtti）
- gmock 侧 2 个 py_test（gmock_leak_test/gmock_output_test）**上游默认形态不注册**：
  find_package(Python3) 只在 googletest/ 子目录作用域（internal_utils.cmake）执行，
  父作用域 googlemock 的 py_test 宏因 Python3_Interpreter_FOUND 未定义而 return。
  这是上游 BUILD_GMOCK=ON 入口形态的固有行为，非适配缺失。

**实跑结果：63/63 全部通过（100%）**，OHOS PC 真机（本机 HarmonyOS aarch64），
`env TMPDIR=$HOME/tmp/gt-tmp LD_LIBRARY_PATH=/system/lib64 ctest`：
- 47 个 C++ 测试二进制直接运行通过
- 16 个 Python 驱动测试（py_test）通过
- 需 TMPDIR（patch 0001）与 gtest_help_test 平台判定 patch（patch 0002）支撑

与 gtest/1.17.0 PR（59/65，90.8%）差异说明：该 PR 未打 gtest_help_test 平台判定
patch 且统计口径含 2 个上游未注册的 gmock py_test；本包打齐 2 个 portability patch
后 63/63 全过（注册口径 63）。

## 补丁

1. `0001-tmpdir-ohos-sandbox.patch` — gtest-port.cc mkstemp 临时目录改为读 TMPDIR
   （OHOS 沙箱 /tmp 只读，否则死亡测试/流捕获测试失败）；与 gtest/1.17.0.1 同款。
2. `0002-gtest-help-ohos-platform-detect.patch` — gtest_help_test.py 平台判定：
   OHOS uname[0]='HarmonyOS' 使 IS_LINUX 误判 False 而错走 assertNotIn 分支；
   将 HarmonyOS 归入 Linux 族（断言逻辑不变）；与 googletest/1.12.1 的 0003 同款
   （适配 1.17.0 行文）。

## test_package（消费者测试）

- find_package(GTest REQUIRED CONFIG) + 链接 GTest::gtest_main 与 GTest::gmock
  ——与下游消费者（scnlib tests/cmake/dependencies.cmake）完全一致的消费形态
- 3 个 TEST：EXPECT_EQ 断言 + HasSubstr 匹配器 + MOCK_METHOD 模拟对象
- 运行：`bash -c "LD_LIBRARY_PATH=/system/lib64 ./test_googletest"`（scnlib 先例
  同款，OHOS musl ld.so 从 /system/lib64 解析 libc++_shared.so），3/3 通过

## 依赖

- 无外部 Conan 依赖（零依赖库）

## 提交记录

- 2026-09-12 本地全流程验证通过（conan-verify G0-G4/L2/L4/L5 + W3 本地 CI 模拟
  L0/L1/L4/L5 全绿 + 上游 63/63 + test_package 3/3），提交 PR
- PR 正文统计口径：上游注册 N=63（ctest -N 实测）；适配后 63/63（100%）+ 消费者 1
---

**编译结束**: 2026-09-12 17:37
**最终状态**: built
