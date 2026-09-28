# Test Report — flatbush 1.5.0（r02 返工更新）

## Build Status
- **Compiler**: Clang 15.0.4 (aarch64 OHOS, /data/service/hnp/bin/clang++)
- **Build System**: CMake (header-only INTERFACE target + fuzztest 框架)
- **Build Status**: success（conan create ohos-aarch64 通过；fuzz_test 以
  `-DWITH_FUZZING=ON -DFUZZTEST_FUZZING_MODE=ON` 构建通过）

## 双口径测试台账（上游测试，r02 全量纳入）

### 源码声明总数（source_declared_total）
按官方 tag v1.5.0 源码可复制枚举规则：

| 入口 | 声明 | 分类理由 | 是否独立上游用例 |
|------|------|----------|------------------|
| test.cpp | 70 × `TEST(FlatbushTest, …)` | 用户测试源独立用例 | ✅ 是 |
| test.cpp | 5 × `TYPED_TEST(FlatbushTypedTest, …)` × 8 类型 | 用户测试源类型实例化（int8..double 8 种）→ gtest 注册 40 例 | ✅ 是（gtest 按 8 类型展开为 40 例） |
| fuzz.cpp | 24 × `FUZZ_TEST(FlatbushFuzzTest, …)` | fuzztest 框架用户用例（FuzzFrom/Search/Neighbors × 8 类型） | ✅ 是（fuzz 框架独立用例，r02 已构建运行） |
| header-smoke.cpp | 1（仅 `#include "flatbush.h"`） | 编译冒烟，无测试断言 | ❌ 否（编译入口） |
| bench.cpp | 7 × `BENCHMARK(…)` | google/benchmark 基准 | ❌ 否（基准非测试用例） |
| tests/package/main.cpp | 1（find_package 消费者） | package 消费者用例（与 test_package 消费者同型） | ✅ 是（消费者用例） |

### 统计口径（r02 全量）

**独立上游用例总数 = 134**（110 单元 + 24 fuzz）

- **源码声明总数（source_declared_total）**：134
  - test.cpp 75 个宏声明（70 TEST + 5 TYPED_TEST，gtest 实例化 110 例）
  - fuzz.cpp 24 个 FUZZ_TEST 声明（fuzztest 注册 24 例）
- **配置可执行数（configured_executable_total）**：134
  - unit_test 目标注册 110 例（70 TEST + 5 TYPED_TEST × 8 类型）
  - fuzz_test 目标注册 24 例（WITH_FUZZING=ON + FUZZTEST_FUZZING_MODE=ON）
- **实际执行并通过（executed_passed_total）**：134
  - unit_test：110/110 PASS（`[==========] 110 tests from 9 test suites ran. [ PASSED ] 110 tests.`）
  - fuzz_test：24/24 PASS（`[==========] 24 tests from 1 test suite ran. [ PASSED ] 24 tests.`，24036 ms）
- **失败数**：0
- **未运行/未实例化数**：0（r01 曾将 fuzz 24 项列为未实例化；r02 已全量纳入并运行通过）
- **全量通过率**：**134/134 (100%)**

### 逐项映射（源码声明 → 构建条件 → 目标 → 注册 → 日志）
- `TEST/TYPED_TEST`（test.cpp）→ `WITH_TESTS=ON` → `unit_test` 目标
  → `gtest_discover_tests` 注册 110 例 → `./build-unit/unit_test` 全部 PASS
  （日志 reports/unit-test-full-run.log，SHA-256 b9a012ea54f17599defbf1f9c4d937b10ab75c0fdaf903fc6d876d49e96e768c）
- `FUZZ_TEST`（fuzz.cpp）→ `WITH_FUZZING=ON -DFUZZTEST_FUZZING_MODE=ON`（另
  -DFUZZTEST_BUILD_TESTING=OFF、-DCMAKE_SYSTEM_NAME=Linux 规避 antlr4 对
  HarmonyOS 未知系统的 C++17 误判、FETCHCONTENT_SOURCE_DIR_* 指向本地已校验
  依赖源码）→ `fuzz_test` 目标 → fuzztest 注册 24 例 →
  `./build-fuzz/fuzz_test` 逐入口运行全部 PASS（日志 reports/fuzz-test-full-run.log，
  SHA-256 3bf672ff2064b71d28552ed0e3fdefcfb6ef32ecb6c32bdfb01c53c4ee976b89）
- `BENCHMARK`（bench.cpp）→ `WITH_BENCHMARKS=ON` → `bench_test` 目标 → 基准非测试用例，台账列出
- `tests/package/main.cpp` → find_package consumer → `package_test` → `ctest` PASS

### fuzz 依赖拉取与核验（r02，不得沿用旧 skip）
| 依赖 | 版本/提交 | 来源 | 校验和 |
|------|----------|------|--------|
| fuzztest | 2025-08-05 | github.com/google/fuzztest tag | tar.gz SHA-256 4cc64d8171cfa4a4fa27099c130104a24157746d57337f6df3a9ef9a6e62fb5d |
| abseil-cpp | d04b964d82ed5146f7e5e34701a5ba69f9514c9a | github.com/abseil/abseil-cpp commit | tar.gz SHA-256 ef1e132b110a012e249f7d3e15c04c0183c014b3036afc22c8a9a96e13f77420 |
| re2 | 2024-07-02 | github.com/google/re2 tag | tar.gz SHA-256 eb2df807c781601c14a260a507a5bb4509be1ee626024cb45acbd57cb9d4032b |
| googletest | v1.16.0（fuzztest 需要） | github.com/google/googletest tag | tar.gz SHA-256 78c676fc63881529bf97bf9d45948d905a66833fbfa5318ea2cd7478cb98f399 |
| antlr4-cpp-runtime | 4.12.0 | www.antlr.org 官方下载 | zip MD5 acf7371bd7562188712751266d8a7b90（与 fuzztest BuildDependencies.cmake 声明一致） |

registry 复核（r02 最终回报前）：fuzztest/antlr4 在 ohpcd 无配方（0 匹配，官方源直拉）；
gtest/1.17.0.x、abseil/20260526、re2/2024-04-01 已在仓（框架按 pin 版本直拉源码，属
框架依赖基础设施，已在本地构建验证通过）。

## 鸿蒙专项测试（reports/ohos-test.cpp）
- 编译：`clang++ -std=c++17 -DFLATBUSH_SPAN -I <conan 已安装 include>`
- 运行：`PASS: OHOS C++17/FLATBUSH_SPAN + JS-compatible roundtrip ok`（exit 0）
- 验证点：C++17 消费、FLATBUSH_SPAN 宏传播、JS 兼容字节布局 from/data 往返、fromView

## test_package（L1）
- conan create 内自动执行：`PASS: flatbush L1 consumer test ok (1 bbox hit, 3 neighbor(s), rebuilt ok)`
- 消费者用例（仅公开头文件/API）：FlatbushBuilder.add/finish/search/neighbors/from

## 门禁结论
- L0（junk_check）：pass（PR diff 模式不含基线文件）
- L1（test_package 实际执行）：pass
- L2（smoke）：skip（无 bin/ 目录，header-only 库）
- L4（安全扫描）：pass
- L5（产物基线）：warn（无 lib/bin 产物，header-only 属预期）

## Known Issues
- 无。fuzz_test 24 项已全量构建并运行通过（r02），不再有未运行/未实例化入口。