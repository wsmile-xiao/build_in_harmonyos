# greg7mdp-gtl 1.2.0 适配笔记

## 编译环境
- 构建系统: cmake（上游根 `CMakeLists.txt` 同时驱动库目标与测试树；库本体为 INTERFACE 目标，无编译产物）
- 编译日期: 2026-09-29
- 编译器: clang 15.0.4 / clang++（OHOS aarch64，libc++）
  - 原生轮（pristine tarball）：`CMAKE_CXX_STANDARD=20`（上游默认）
  - conan 轮（本配方）：**C++17** —— profile 的 `compiler.cppstd=17` 经 `conan_toolchain.cmake`
    写成 `CMAKE_CXX_STANDARD=17`，上游 `if(NOT CMAKE_CXX_STANDARD)` 见其已定义即沿用 17；
    日志原文 `-- Conan toolchain: C++ Standard 17 with extensions OFF`（conan-create.log:93）
  - 两轮 2207/2207 全过；只有 `test_package/CMakeLists.txt` 显式覆盖回 20
    （conan-create.log:5481 `… CMAKE_CXX_STANDARD value … to 17 has been modified to 20 by …/test_package/CMakeLists.txt`）
- 状态: built
- 交付形态: **header-only**（`package_type = "header-library"`，`package_id` 清空为单一 ID，
  交付物仅 `include/gtl/**` + `licenses/LICENSE`）

## 编译步骤

1. 源码：`get()` 自 `https://github.com/greg7mdp/gtl/archive/refs/tags/v1.2.0.tar.gz`
   （sha256 `1547ab78…c6ba8e7`，与 conan-center-index `recipes/greg7mdp-gtl/all/conandata.yml`
   的 1.2.0 条目全值逐字一致）。**无补丁**，源码树与发布 tarball 逐字节一致。
2. `generate()`：`CMakeDeps` 生成 `GTest` 目标（来自 `test_requires` 的 `gtest/1.17.0.2`）；
   `CMakeToolchain` 注入 5 个缓存变量：

   | 变量 | 值 | 作用 |
   |---|---|---|
   | `CMAKE_PROJECT_INCLUDE` | `<build>/gtl-gtest-inject.cmake` | 在上游 `project(gtl …)` 之后 `find_package(GTest CONFIG REQUIRED)`，定义 `GTest::gmock_main` |
   | `GTL_GTEST_LIBS` | `GTest::gmock_main` | 上游自带开关：非空即**整段跳过** `include(cmake/DownloadGTest.cmake)` |
   | `GTL_BUILD_TESTS` | `ON` | 构建上游 20 个测试目标 |
   | `GTL_BUILD_EXAMPLES` | `OFF` | 不构建 examples（该分支才会 `find_package(Threads)`） |
   | `GTL_BUILD_BENCHMARKS` | `OFF` | 不构建 benchmarks |

3. `build()`：`cmake.configure()` + `cmake.build()` 编译 20 个上游测试目标，
   然后**逐个真跑** `--gtest_also_run_disabled_tests`、解析 gtest 汇总行计数，
   并先跑一次 `--gtest_list_tests` 校验「注册数 == 运行数」，任一不符或任一 case 失败即构建失败。
4. `package()`：只拷 `include/` → `include/`、`LICENSE` → `licenses/`。
5. `test_package`：消费者 `#include <gtl/…>` + 45 个显式检查，`test()` 直跑二进制。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游测试树在 configure 期 `git clone https://github.com/google/googletest.git GIT_TAG main` | `cmake/CMakeLists.txt.in` 的 `ExternalProject_Add` 未固定版本，既不可复现又在离线 worker 上必失败 | 不打补丁：置 `GTL_GTEST_LIBS` 缓存变量让上游自己跳过整个 `DownloadGTest` 分支，gtest 改由 conan `test_requires` 提供 |
| 2 | 跳过 `DownloadGTest` 后 `GTest::gmock_main` 目标无人定义 | 上游假定父工程已经 `add_subdirectory` 了 googletest | `CMAKE_PROJECT_INCLUDE` 片段在 `project(gtl)` 之后 `find_package(GTest CONFIG REQUIRED)`（`GTestConfig.cmake` 由 CMakeDeps 生成） |
| 3 | `conan_data["sources"]` 取值报 `TypeError: get() got an unexpected keyword argument '1.2.0'` | conandata 写成了 CCI 的按版本分层形态（`sources: "1.2.0": {...}`），而本仓库配方用扁平形态 | 改写为扁平 `sources: url/sha256`（与仓库其它配方、与 `templates` 一致） |
| 4 | gtest 解析正则首版报 `cannot parse GoogleTest summary` | gtest 汇总行实际是 `[==========] 12 tests from 1 test suite ran. (40 ms total)`，尾部带耗时，正则用了 `$` 行尾锚 | 去掉 `ran\.` 后的 `$` 锚，只锚行首 |
| 5 | `emmintrin.h` / `tmmintrin.h` 出现在 `include/gtl/gtl_config.hpp` | x86 SSE 快路径 | 两处均在 `#if GTL_HAVE_SSE2` / `#if GTL_HAVE_SSSE3` **条件块内**，宏由 `__SSE2__`/`__SSSE3__` 推导；aarch64 编译探针输出 `GTL_HAVE_SSE2=0 GTL_HAVE_SSSE3=0`，`phmap.hpp` 走 `GroupPortableImpl` 通用路径 —— **可收，不是止损项** |
| 6 | `gtest/1.17.0`（ohpcd 基线版）只有单一 `gtest::gtest` 目标 | 该版 `package_info` 未设 components | 选 `gtest/1.17.0.2`（`cmake_file_name=GTest` + `GTest::gtest_main/gmock/gmock_main` 分量目标），`conan install --build=never` 实测二进制可得 |
| 7 | conan 轮的 C++ 标准与原生轮不同（17 vs 20） | profile `compiler.cppstd=17` 被 `conan_toolchain.cmake` 写成 `CMAKE_CXX_STANDARD=17`，上游 `if(NOT CMAKE_CXX_STANDARD)` 见其已定义即不再改写为 20 | **如实记录，不强行覆盖**：gtest 1.17 要求 ≥C++17，两轮 2207/2207 全过；`test_package/CMakeLists.txt` 显式钉 20 作为消费端默认。若需 conan 轮也走 20，在 `generate()` 加 `tc.cache_variables["CMAKE_CXX_STANDARD"]="20"`（本轮未加，避免与 profile `cppstd=17` 不一致） |

## 源码修改

**无。** `patches_applied: []`，源码树与发布 tarball 逐字节一致；上游测试用例本体零改动。
测试构建树的行为变化全部由配方层缓存变量与 `CMAKE_PROJECT_INCLUDE` 片段承担。

## 依赖版本

- 运行期依赖：无（header-only，纯标准库）。
- 测试期依赖（`test_requires`，不进交付依赖）：`gtest/1.17.0.2`（ohpcd 在档，
  `conan install --requires=gtest/1.17.0.2 --build=never -r=ohpcd` 实测二进制可得）。

## 上游测试清点与申报（R51 三步法）

**第一步·清点**（取数命令）：

```bash
# 候选口径 1 —— 源码宏数（tests/ 下 .cpp/.hpp/.h，含包装文件与共享测试体）
grep -rhE '^[[:space:]]*(TEST|TEST_F|TEST_P|TYPED_TEST|TYPED_TEST_P|TYPED_TEST_F)\(' tests/ | wc -l   # → 367
#   其中 TEST 249 + TEST_F 30 + TYPED_TEST_P 88

# 候选口径 2 —— 框架注册数（运行期 gtest，20 个二进制求和）
for b in test_*; do ./$b --gtest_list_tests; done        # → 2207

# 候选口径 3 —— ctest 程序口径（非用例口径，仅记录）
ctest --test-dir <build> -N                               # → 20 个测试程序

# 候选口径 4 —— 上游当前 HEAD 下界（rule4）
git clone --depth 1 --sparse https://github.com/greg7mdp/gtl && git sparse-checkout set tests
grep -rhE '^[[:space:]]*(TEST|TEST_F|TEST_P|TYPED_TEST|TYPED_TEST_P|TYPED_TEST_F)\(' tests/ | wc -l   # → 376（HEAD 086db66）
git show HEAD:CMakeLists.txt | grep -c 'gtl_cc_test(NAME'                                            # → 20（与 tag 同值）
```

| 候选口径 | 数值 | 说明 |
|---|---|---|
| 源码宏数（词面清点，v1.2.0） | **367** | `TEST` 249 + `TEST_F` 30 + `TYPED_TEST_P` 88，按**文件**各计 1 次 |
| 框架注册数（`--gtest_list_tests`，v1.2.0） | **2207** | 20 个二进制求和，含 2 个 `DISABLED_*` |
| ctest 程序数（v1.2.0） | 20 | 「测试程序数」不是用例口径（zfp 教训），不作为 N |
| 上游当前 HEAD 源码宏数（下界读数） | 376 | HEAD = `086db66`（v1.2.0 之后唯一一次提交 `Fix rehash(0) … (#58)`），比 tag 多 9 个宏；`gtl_cc_test` 目标数仍为 20 |

**N = max(367, 2207) = 2207。**（HEAD 下界读数 376 属**源码宏口径**，与 2207 不同口径，
不参与取大；审方按宏口径独立清点时实测 ≤ 376 < 2207，不存在少报。）

差额 2207 − 367 = **1840** 逐项归因（按实测注册数反推，四项相加恰为 1840）：

| 归因 | 用例数 | 计算方式 / 说明 |
|---|---|---|
| `TYPED_TEST_P` 按类型实例化 | **+1806** | 直接 target 注册 2171 − 直接 target 文件级宏 353 − vector 双展开 17 + 未注册宏 5。88 个 `TYPED_TEST_P` 词面宏经 `INSTANTIATE_TYPED_TEST_SUITE_P` 对每个元素类型各生成一份 case，词面只能数出 88 |
| `parallel_*` 5 个包装 target 重复编译共享测试体 | **+22** | 5 个包装 target 共实例化 36 个 case（map 族 8×3、set 族 6×2），减去共享体两个文件本身已计入文件级清点的 14（8+6）。`parallel_flat/node_hash_map/set_test.cpp` 与 `parallel_flat_hash_map_mutex_test.cpp` 各只有 127–340 字节，内容是 `#define THIS_HASH_MAP …` + include 共享测试体，共享体本身没有独立 target |
| `vector_test.cpp` 两次 `#include "./vector_test.cpp.h"` | **+17** | 同一 .h 在两个命名空间各展开一次（21 + 17 + 17 = 55，与实测吻合） |
| 文件级宏中未被注册的部分 | **−5** | `raw_hash_set_test.cpp` 76→73（−3）、`btree_test.cpp` 71→69（−2），位于未被引用的代码块 |
| **合计** | **+1840** | 1806 + 22 + 17 − 5 = 1840 = 2207 − 367 |

以**框架注册数 2207** 为 N；源码宏数与框架注册数两种口径不混用——assertion 数与消费者断言数另行列出。

**第二步·运行**（两轮同一读数，设备实测 2026-09-29）：

- 轮 A 原生（pristine 源码树 + 上游自带 `DownloadGTest`，CMake 4.1.2，`-DCMAKE_CXX_STANDARD=20`）：
  `ctest` 20/20 程序通过；逐程序 `--gtest_also_run_disabled_tests` 求和
  `TOTAL_RAN=2207 TOTAL_PASSED=2207`。
- 轮 B conan（本配方 `build()` 内真跑，`conan create` rc=0）：
  `HMBS_UPSTREAM_TEST_RESULT={"status":"passed","framework":"gtest",
  "source_macro_total":367,"registered_total":2207,"executed":2207,"passed":2207,
  "failed":0,"skipped":0,"not_run":0}`（逐二进制明细见该行 `binaries` 字段）。

`TOTAL = PASS + FAIL + SKIP + NOT_RUN = 2207 + 0 + 0 + 0 = 2207`，
`N′ = 2207`，通过率 2207/2207（100%）。

> `DISABLED_*` 说明：上游 `tests/phmap/raw_hash_set_test.cpp:1088/1188` 有 2 个
> `DISABLED_` 前缀用例（默认 `./test_raw_hash_set` 只跑 71/73）。本轮统一加
> `--gtest_also_run_disabled_tests` 全量执行，实测 2 个用例各约 1s、全部通过，
> 因此分母与分子同为 2207，**不存在未运行项**。

**第三步·申报**：PR 正文上游表首行行值 = 2207（单元测试），其余行 0；
鸿蒙特有测试行 = `test_package` 消费者断言 **45**（不进上游分母）。

## 验证结果

```bash
# ① 原生构建 + 上游测试（pristine tarball）
cmake -S gtl-1.2.0 -B build -DCMAKE_BUILD_TYPE=Release \
      -DGTL_BUILD_TESTS=ON -DGTL_BUILD_EXAMPLES=OFF -DGTL_BUILD_BENCHMARKS=OFF \
      -DCMAKE_CXX_STANDARD=20 && cmake --build build -j4      # BUILD_RC=0
ctest --test-dir build --output-on-failure -j2                 # 100% tests passed, 0 failed out of 20
./build/test_<x> --gtest_also_run_disabled_tests  # 逐程序求和 TOTAL_RAN=2207 TOTAL_PASSED=2207

# ② Conan 配方验证（conan create，本仓库配方）
conan create archives/g/greg7mdp-gtl/1.2.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=… -c tools.build:jobs=4   # rc=0
#   HMBS_UPSTREAM_TEST_RESULT=… executed 2207 / passed 2207 / failed 0
#   gtl consumer checks: 45 run, 0 failed
```

## 交付物

| 文件 | 说明 |
|------|------|
| `include/gtl/*.hpp` | header-only 库本体（20 个 `.hpp` + `debug_vis/{gtl.natvis,gtl_gdb.py,gtl_lldb.py}` = include 下 23 个文件），与 tarball 源逐字节一致 |
| `licenses/LICENSE` | MIT 许可证 |

## 注意事项

- **有 x86 SSE 快路径**：`gtl_config.hpp` 条件引入 `emmintrin.h`/`tmmintrin.h`，
  `phmap.hpp` 的 `GroupSse2Impl` 只在 `GTL_HAVE_SSE2=1` 时编译。aarch64 上两宏恒为 0，
  实测构建面不引用任何 x86 内建函数；`test_package` 会把 `GTL_HAVE_SSE2/GTL_HAVE_SSSE3`
  打出来作为留证（设备上为 0/0）。
- **header-only 交付形态**：conan-verify 的 G4/L2/L4/L5 对 `header-library` 走
  「跳过分支却并列打 ✅」（device-facts §二.17），自动报告的 ✅ 不可采信；
  须人工补测，读数落 `reports/conan-verify-supplement.md`。
- 上游无 `commands.json` 需求：`package_type = "header-library"`、`cpp_info.bindirs = []`，
  属纯库包（PF8/L0k 口径：库包不得有 `commands.json`）。
