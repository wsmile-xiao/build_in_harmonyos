# boolinq 3.0.4 适配笔记

## 编译环境
- 构建系统: cmake（上游根 CMakeLists 仅用于测试树；库本体为单头文件，无编译产物）
- 编译日期: 2026-09-25
- 编译器: clang 15.0.4 / clang++（OHOS aarch64，libc++，C++17）
- 状态: built
- 交付形态: **header-only**（`package_type = "header-library"`，`package_id` 清空为单一 ID
  `da39a3ee…80709`，交付物仅 `include/boolinq/boolinq.h` + `licenses/LICENSE`）

## 编译步骤

1. 源码：`get()` 自 `https://github.com/k06a/boolinq/archive/3.0.4.tar.gz`
   （sha256 `3cbee2b5…aed45`，与 conan-center-index `recipes/boolinq/all/conandata.yml` 全值逐字一致），
   随后 `apply_conandata_patches()` 打 2 个补丁（仅作用于测试构建树，不动头文件）。
2. `generate()`：CMakeDeps 生成 boolinq 目标；CMakeToolchain 注入 `GTest_DIR`
   指向 conan `gtest/1.17.0` 包的 `lib/cmake/GTest`。
3. `build()`：`cmake.configure()` + `cmake.build()` 编译上游两个测试目标
   `boolinq-test`（38 个翻译单元）与 `boolinq-test14`（GroupByTestComplex），
   然后**真跑**两个二进制、解析 gtest 汇总行计数，任一失败即构建失败。
4. `package()`：只拷贝 `include/` → `include/`、`LICENSE` → `licenses/`。
5. `test_package`：消费者 `#include <boolinq/boolinq.h>` + 26 个显式检查，`test()` 直跑二进制。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 根 `CMakeLists.txt` 的 `CMAKE_MINIMUM_REQUIRED (VERSION 3.0)` 在 CMake 4.1.2 直接硬错误 | CMake 4.x 移除了对 <3.5 的兼容 | 补丁 0001 抬到 `cmake_minimum_required (VERSION 3.15)` |
| 2 | `ADD_SUBDIRECTORY (externals/googletest)` 等报 "does not contain a CMakeLists.txt" | release tarball **不含 git 子模块内容**（`.gitmodules` 指向 googletest/benchmark，tarball 里是空目录） | 补丁 0001 删除 externals/googletest、externals/benchmark、bench 三个子目录与失效的 `ADD_DEPENDENCIES … gtest/benchmark` |
| 3 | 上游测试链裸名 `gtest`/`gtest_main` 目标无定义 | 目标本应由子模块提供 | 补丁 0002 改 `find_package(GTest CONFIG REQUIRED)` + `GTest::gtest_main`/`GTest::gtest`（`GTest_DIR` 由 generate() 指向 conan gtest 包） |
| 4 | gtest/1.17.0 头文件在 `-std=c++11`/`-std=c++14` 下编译失败（设备实测 rc=1） | gtest 1.17 硬要求 C++17 | 补丁 0002 把测试树 `CMAKE_CXX_STANDARD 11` → `17`（boolinq 头本身无 C++17 移除特性，实测兼容） |
| 5 | 全局 `-fprofile-arcs -ftest-coverage` gcov 插桩 | 上游默认带覆盖率构建，设备无 lcov/gcov 链路且会给纯测试构建引入插桩 | 补丁 0002 删除该行（覆盖率报告目标保留但不构建，不影响测试结果） |

## 源码修改

- `patches/0001-CMakeLists.txt.patch`（portability，非平台专属）：CMake 版本下限 + 删空子模块子目录。
- `patches/0002-test-CMakeLists.txt.patch`（conan 集成，非平台专属）：接 Conan GTest + C++17 + 去 gcov flags。
- 两补丁均经 `refresh-patch --auto` 由 difflib 生成，`patch --dry-run -p1` 对 pristine 源通过，
  实际 apply 后与工作树逐字节 `diff -r` 一致；**上游测试用例本体（40 个 .cpp）零改动**。

## 依赖版本

- 运行期依赖：无（header-only，纯标准库）。
- 测试期依赖（`test_requires`，不进交付依赖）：`gtest/1.17.0`（ohpcd 在档，`conan install --build=never` 实测二进制可得）。

## 上游测试清点与申报（R51 三步法）

**第一步·清点**（取数命令）：

```bash
# 源码宏数（候选口径 1）
grep -rhoE '^[[:space:]]*TEST(_F|_P)?[[:space:]]*\(' test/*.cpp | wc -l   # → 214
# 框架注册数（候选口径 2，运行期 gtest 汇总行）
./boolinq-test     → "[==========] 213 tests from 40 test suites ran." / "[  PASSED  ] 213 tests."
./boolinq-test14   → "[==========] 1 test … ran."        / "[  PASSED  ] 1 test."
# ADD_TEST 注册数（ctest 套件口径）
grep -c '^ADD_TEST' test/CMakeLists.txt                  # → 2
# 上游当前 HEAD 下界（rule4）
git clone --depth 1 --sparse https://github.com/k06a/boolinq && git sparse-checkout set test
grep -rhoE '^\s*TEST(_F|_P)?\s*\(' test/*.cpp | wc -l   # → 214（HEAD 2f0e6485）
```

| 候选口径 | 数值 | 说明 |
|---|---|---|
| 源码宏数 `TEST(...)` | **214** | 39 个含用例的 .cpp（`main.cpp` 0 个；test/ 共 40 个 .cpp） |
| 框架注册数（gtest 运行期） | **214** | 213（boolinq-test）+ 1（boolinq-test14） |
| ADD_TEST 注册数 | 2 | ctest 套件口径，非用例口径，不作为 N |
| 上游当前 HEAD 下界 | 214 | 与被审版本同值，无差额 |

**N = max(214, 214) = 214，差额 0**（无需归因项）。

**第二步·运行**（`conan create` 的 `build()` 内真跑，设备实测 2026-09-25）：
`TOTAL = PASS + FAIL + SKIP + NOT_RUN = 214 + 0 + 0 + 0 = 214`，
`N′ = 214`，通过率 214/214（100%）。原始日志见 `reports/conan-create.log`（采信轮证据副本）。

**第三步·申报**：PR 正文上游表首行行值 = 214（单元测试），其余行 0；鸿蒙特有测试行 =
`test_package` 消费者断言 **26**（不进上游分母）。

## 验证结果

```bash
conan create archives/b/boolinq/3.0.4 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=… --build=missing
# rc=0；HMBS_UPSTREAM_TEST_RESULT={"status":"passed","framework":"gtest",
#   "source_declared_total":214,"executed":214,"passed":214,"failed":0,"skipped":0,
#   "binaries":{"boolinq-test":213,"boolinq-test14":1}}
# test_package: "boolinq consumer checks: 26 run, 0 failed"
```

## 交付物

| 文件 | 说明 |
|------|------|
| `include/boolinq/boolinq.h` | 单头文件库本体（sha256 7a3996f7…904fb，与 tarball 源逐字节一致） |
| `licenses/LICENSE` | MIT 许可证 |

## 注意事项

- **header-only 交付形态**：conan-verify 的 G4/L2/L4/L5 对 `header-library` 走「跳过分支却并列打 ✅」
  （device-facts §二.17），自动报告的 ✅ 不可采信；须人工补测，读数落
  `reports/conan-verify-supplement.md`，消费者面按 device-facts §二人工补测。
- 补丁只动测试构建树，不改库头文件与上游测试用例；消费者 `#include <boolinq/boolinq.h>` 为唯一交付面。
