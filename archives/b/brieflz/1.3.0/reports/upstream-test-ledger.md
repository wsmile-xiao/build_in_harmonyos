# brieflz 1.3.0 上游测试全量枚举台账（双口径）

生成时间: 2026-09-19
枚举范围: 官方 tag v1.3.0 解压全树（.orig 基线, $TMPDIR/builds/brieflz-1.3.0.orig）
构建配置: ohos-aarch64 profile, os=OHOS arch=armv8 clang-15 libc++ cppstd=17, shared=False

## 一、测试相关入口全量清单（分类标注）

| 路径 | 类别 | 是否独立上游用例 | 分类理由 | 实际运行 | 结果/原因 |
|------|------|-----------------|---------|---------|----------|
| test/test_brieflz.c `TEST pack_nothing` (:122) | 用户测试源 | **是（独立用例 1）** | greatest.h 用户 TEST 定义 | 是 | 通过 |
| test/test_brieflz.c `TEST pack_zeroes` (:136) | 用户测试源 | **是（独立用例 2）** | 同上 | 是 | 通过 |
| test/test_brieflz.c `TEST pack_numbers` (:167) | 用户测试源 | **是（独立用例 3）** | 同上 | 是 | 通过 |
| test/test_brieflz.c `TEST pack_alternate` (:199) | 用户测试源 | **是（独立用例 4）** | 同上 | 是 | 通过 |
| test/test_brieflz.c `TEST pack_random` (:231) | 用户测试源 | **是（独立用例 5）** | 同上 | 是 | 通过 |
| test/test_brieflz.c `TEST pack_random_start` (:286) | 用户测试源 | **是（独立用例 6）** | 同上 | 是 | 通过 |
| test/test_brieflz.c `TEST pack_random_end` (:340) | 用户测试源 | **是（独立用例 7）** | 同上 | 是 | 通过 |
| test/test_brieflz.c `TEST depack_nothing` (:393) | 用户测试源 | **是（独立用例 8）** | 同上 | 是 | 通过 |
| test/test_brieflz.c `TEST depack_safe_errors` (:409) | 用户测试源 | **是（独立用例 9）** | 同上 | 是 | 通过 |
| test/test_brieflz.c `TEST depack_safe_random` (:425) | 用户测试源 | **是（独立用例 10）** | 同上 | 是 | 通过 |
| test/test_brieflz.c `SUITE(BriefLZ)` + `RUN_TEST*` (:442-470) | SUITE/驱动 | 否 | 注册与调度层：level 1..10 循环实例化上述用例，非独立用例 | 已运行 | 循环产生 70 个 RUN_TEST 运行实例 |
| test/greatest.h（10 处 TEST 宏） | 框架头 | 否 | 测试框架宏定义（greatest.h），非用户用例 | 编译引用 | 框架 |
| include/brieflz.h / src/*.c | 被测库源码 | 否 | 库代码非测试 | 编译通过 | libbrieflz.a |
| example/blzpack.c + parg.c | 样例/示例程序 | 否 | 示例程序（可执行 blzpack），非独立测试用例 | 构建（L2 验证） | 样例不计入；blzpack --version OK |
| Doxyfile / NEWS / README.md | 文档 | 否 | 非测试 | 不适用 | - |
| CMakeLists.txt `add_test("brieflz" test_brieflz)` | 构建目标/注册 | 否 | CTest 注册项（1 个），驱动 test_brieflz | 已执行 | ctest 1/1 Passed |

## 二、口径汇总

**source_declared_total（源码声明独立用例）**: **10**（test/test_brieflz.c 中 10 个独立 TEST 定义）
**configured_executable_total（当前配置实例化/注册可执行用例数）**: 10 个独立用例全部实例化
（编译为一个 test_brieflz 可执行；SUITE 按压缩级别 1..10 循环，实际运行实例 70 个 RUN_TEST）
**executed_passed_total**: **10/10**（70/70 运行实例通过）
**失败数**: 0　**未运行/未实例化**: 0
**全量通过率**: **10/10 = 100%**（executed_passed_total/source_declared_total）
当前配置可执行集合通过率: 70/70 = 100%（另列，不替代全量口径）

映射: 源码 TEST 定义（test/test_brieflz.c:122-425）
→ 构建条件 BRIEFLZ_BUILD_TESTING=ON（CMakeLists option）
→ 构建目标 test_brieflz（add_executable + add_test）
→ ctest -N 注册 1 项 / greatest SUITE 注册 70 个 RUN_TEST
→ 实际执行日志: `70 tests - 70 passed, 0 failed, 0 skipped (18514731 ticks, 18.515 sec)`、`482153 assertions`、ctest `1/1 Test #1: brieflz ... Passed 19.42 sec`、rc=0

## 三、实际执行记录

- 本地: `cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DBRIEFLZ_BUILD_TESTING=ON`（rc=0）
  → `make -j4`（rc=0）→ `ctest --output-on-failure`（rc=0, 1/1 Passed, 19.42s）
  → `./test_brieflz`（rc=0, 70/70 passed, 18.515s, 482153 assertions）
- Conan: `conan-verify` G2 `conan create`（rc=0），build() 内 `cmake.test()` 同样 1/1 Passed
- 无依赖考虑（0 依赖），无 /tmp 受限、无 LD_LIBRARY_PATH skip 场景（全部在本平台实际运行）