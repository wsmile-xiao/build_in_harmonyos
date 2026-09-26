# protobuf 21.12 适配笔记（3.21 线，无 Abseil）

## 编译环境
- 构建系统: cmake（测试经 ctest / gtest 运行）
- 编译日期: 2026-09-06
- 编译器: clang 15 (aarch64 OHOS)
- 状态: published（本 PR）

## 背景（为何新增此版本）
OLA 0.10.9 依赖 protobuf，但 OLA 代码仍是 C++11 世代（648 处
`std::auto_ptr`，`std::auto_ptr` 在 C++17 已被删除）。制品仓中已有
protobuf 33.6/33.6.1，其公开头文件经 Abseil 硬性要求 C++17，无法被
OLA 编译。21.12 是最后一代不依赖 Abseil、公开头文件保持 C++11 兼容
的版本（上游 protobuf >= 22 起引入 Abseil）。本 PR 发布该版本作为
OLA 的依赖（R36 依赖先发布）。

## 编译步骤
1. conan create（cmake；protobuf_BUILD_TESTS=ON +
   protobuf_USE_EXTERNAL_GTEST=ON，CONFORMANCE=OFF/EXAMPLES=OFF、
   PROTOC_BINARIES=ON、LIBPROTOC=ON、WITH_ZLIB=OFF）
2. build() 内配置后编译 libprotobuf(lite/protoc) 与上游三个测试目标
   （tests/lite-test/lite-arena-test），随后 `ctest` 执行并收集
   gtest XML（protobuf_TEST_XML_OUTDIR）；XML 汇总逐用例统计以
   "UPSTREAM GTEST SUMMARY" 输出到 conan 日志（实证可查）。
3. package() 中把安装的 protobuf.pc / protobuf-lite.pc 的绝对 prefix
   改写为 `prefix=${pcfiledir}/../..` 相对形式，保证 conan 缓存可迁移。

## 上游测试接入（R51 三步法申报表）
### 1. 清点
- 上游 21.12 无独立 tests/ 目录；测试源为 src/google/protobuf/ 下
  `*_unittest.cc`/`*_test.cc`（实测 `find src -name '*_unittest.cc'
  -o -name '*_test.cc'` = **72** 个翻译单元，另含公共测试支撑文件
  test_util/arena_test_util/reflection_tester/mock_code_generator 等）。
- cmake/tests.cmake 将之编译为 **3 个 gtest 可执行**与 2 个
  ctest 注册项 + `check`（monolithic `tests`，约 90 个 .cc 链接
  libprotoc/libprotobuf + gmock）；运行期共 **2421 个 gtest 用例**
  （gtest XML 计数：tests=2364、lite-test=55、lite-arena-test=2）。
- 版本适配：3.21 与 googletest 1.12.1 同期（vendored 快照 era），
  测试代码零修改编译通过。

### 2. 运行（实测，conan create 内 ctest）
| 测试目标 | gtest 用例 | 通过 | 失败 | 跳过/禁用 |
|---|---|---|---|---|
| lite-test | 55 | 55 | 0 | 0 |
| lite-arena-test | 2 | 2 | 0 | 0 |
| check（`tests` monolithic） | 2364 | 2364 | 0 | 0 |
| **合计** | **2421** | **2421** | **0** | **0** |

- 运行方式：conan create 的 build() 尾部 `ctest --timeout 900
  --output-on-failure --no-tests=error`，每个注册项带
  `--gtest_output=xml:<build>/upstream-tests-xml`，conan 日志输出
  `UPSTREAM GTEST SUMMARY: total=2421 passed=2421 failed=0 disabled=0`
  （构建日志实证，CI 可复核）。
- 实测用时：全包 conan create 约 6 分钟（aarch64 8 核，-j20）；
  ctest 三个目标合计约 27 s。
- 结论：2421/2421 = **100% 通过**，无失败用例、无环境跳过。

### 3. 回填
PR #8393 body 测试数据与本表一致（总用例 2421、通过 2421、
失败 0、跳过 0）；test_package/MANIFEST.yml upstream_tests 逐项列出。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | lang-preflight 误报 python | 检测器把 v21.12 全语言仓库（java/csharp/python/ruby/php 等子目录）统计为 python，忽略主构建系统 CMakeLists.txt | 记录证据后按 cpp 继续（cmake 主工程，上游即 C++ 项目） |
| 2 | 原方案上游单测未引入 | 旧版配方 protobuf_BUILD_TESTS=OFF，误以为必须 configure 期从 GitHub 拉 googletest | 实证 cmake/tests.cmake 自带 `option(protobuf_USE_EXTERNAL_GTEST ... ON)`→`find_package(GTest REQUIRED)`，改用制品仓 googletest/1.12.1 以 test_require 接入（见下） |
| 3 | 首轮 133 用例失败（全为 SetUp/临时文件类，如 `mkdir ... Read-only file system`、`open: No such file or directory`） | OHOS 沙箱 /tmp 只读；protobuf 测试临时目录逻辑（src/google/protobuf/testing/googletest.cc GetTemporaryDirectoryName）只认 Bazel 风格 TEST_TMPDIR，未设置时回退 tmpnam()=P_tmpdir(/tmp) | 配方在运行 ctest 前导出 TEST_TMPDIR 与 TMPDIR 到 build 目录下可写 tmp/（无任何源码补丁）；重测 2421/2421 全绿 |

## 依赖版本
- 运行时/链接依赖：无（21.12 零外部依赖，zlib 默认关闭；package_id
  不受影响）。
- 测试期依赖（test_require，不进入 package_id、不传递给下游）：
  googletest/1.12.1（ohpcd 已发布；cmake_file_name=GTest，组件
  gtest/gtest_main/gmock/gmock_main → GTest::gtest、GTest::gmock、
  GTest::gmock_main 等目标）。注：gtest/1.17.0 制品仅暴露
  gtest::gtest（无 gmock_main/gmock 组件目标），不满足上游 21.12
  测试链接需求，故未采用。

## 验证结果
```bash
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=protobuf/21.12
# 上游 ctest 3/3：lite-test/lite-arena-test/check，2421/2421 gtest 用例通过
# UPSTREAM GTEST SUMMARY: total=2421 passed=2421 failed=0 disabled=0
# test_package: dynamic/pool/arena/parse_error 四场景 + protoc --version（5/5）
```

## 注意事项
- 此版本面向 C++11/C++14 时代消费者（OLA 0.10.9）；新项目应优先使用
  protobuf 33.x。
- 上游测试在每次 conan create 时真实编译执行（CI 的 L1 门禁从构建
  日志取证 "ctest" 与 gtest 汇总），测试失败被计数上报而不会静默
  吞掉：若未来 OHOS 运行环境变化导致用例失败，日志中 UPSTREAM GTEST
  SUMMARY/FAILED CASES 会如实反映（本机实测 0 失败）。
- commands.json / 软件级 manifest 追加 21.12 条目。
---

**编译结束**: 2026-09-06
**最终状态**: built
