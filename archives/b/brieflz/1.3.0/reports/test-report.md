# Test Report — brieflz 1.3.0

**Date**: 2026-09-19
**Build System**: cmake（CMakeLists.txt，brieflz requires CMake >= 2.8.11）
**Platform**: HarmonyOS PC (aarch64, clang-15, libc++, conan ohos-aarch64 profile, shared=False)

## Test Results（双口径台账，详见 reports/upstream-test-ledger.md）

**上游源码声明独立用例数 (source_declared_total)**: 10
（test/test_brieflz.c 内 10 个独立 `TEST` 定义，见 upstream-test-ledger.md 逐项清单）
**当前配置可执行用例数 (configured_executable_total)**: 1 个可执行 test_brieflz
（greatest.h SUITE 按压缩级别 1..10 循环实例化，实际注册 70 个 RUN_TEST 运行实例）
**实际执行并通过 (executed_passed_total)**: 10/10 独立用例全部通过（70/70 运行实例）
**未运行/未实例化**: 0
**全量通过率**: 10/10 = 100%（`executed_passed_total/source_declared_total`；
当前配置可执行集合通过率 70/70 = 100%，ctest 摘要 1/1 Passed）

| 入口 | 源码声明 | 构建条件 | 构建目标 | 执行结果 |
|------|---------|---------|---------|---------|
| 1 pack_nothing | test_brieflz.c:122 `TEST pack_nothing` | BRIEFLZ_BUILD_TESTING=ON | test_brieflz | 通过（70/70 运行实例含入） |
| 2 pack_zeroes | test_brieflz.c:136 `TEST pack_zeroes` | 同上 | test_brieflz | 通过 |
| 3 pack_numbers | test_brieflz.c:167 `TEST pack_numbers` | 同上 | test_brieflz | 通过 |
| 4 pack_alternate | test_brieflz.c:199 `TEST pack_alternate` | 同上 | test_brieflz | 通过 |
| 5 pack_random | test_brieflz.c:231 `TEST pack_random` | 同上 | test_brieflz | 通过 |
| 6 pack_random_start | test_brieflz.c:286 `TEST pack_random_start` | 同上 | test_brieflz | 通过 |
| 7 pack_random_end | test_brieflz.c:340 `TEST pack_random_end` | 同上 | test_brieflz | 通过 |
| 8 depack_nothing | test_brieflz.c:393 `TEST depack_nothing` | 同上 | test_brieflz | 通过 |
| 9 depack_safe_errors | test_brieflz.c:409 `TEST depack_safe_errors` | 同上 | test_brieflz | 通过 |
| 10 depack_safe_random | test_brieflz.c:425 `TEST depack_safe_random` | 同上 | test_brieflz | 通过 |

- 实际执行日志：`./test_brieflz` → `70 tests - 70 passed, 0 failed, 0 skipped
  (18514731 ticks, 18.515 sec)`、`482153 assertions`、`Pass: 70, fail: 0, skip: 0`，rc=0
- ctest：`1/1 Test #1: brieflz ... Passed 19.42 sec`，`100% tests passed, 0 tests failed`
- 源码声明口径：10 个独立 TEST 定义（greatest.h，SUITE 内 level 1..10 循环 + 3 个 depack 直跑）；
  样例（example/blzpack.c）、框架头（greatest.h 10 处框架宏）、脚本均不计入独立用例，已在台账列出。

## 本地真实验证（全部通过）

1. **本地 CMake 配置 + 编译** (rc=0): `cmake .. -DCMAKE_BUILD_TYPE=Release
   -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DBRIEFLZ_BUILD_TESTING=ON` → libbrieflz.a + blzpack + test_brieflz
   （注：上游 CMakeLists 声明 2.8.11，本机 CMake 4.1.2 移除 <3.5 兼容，须传策略下限；见 notes.md）
2. **上游测试** (ctest rc=0): 1/1 Passed；test_brieflz 直接运行 70 实例全部通过（见上表）
3. **Conan 配方门禁** (conan-verify G1-G4 通过): conan create 干净构建通过，
   build() 内 ctest 上游测试通过，test_package 消费者测试 1/1 Passed
4. **消费者用例** (tests/consumer_test.c, rc=0): 仅通过已安装公开头 <brieflz.h> + 公开 API
   （blz_max_packed_size/blz_workmem_size/blz_pack_level/blz_depack/blz_depack_safe）编译链接运行，
   输出 `consumer test OK: packed 65536 -> 18752 bytes (28.61%), round-trip verified`
5. **HarmonyOS 专项测试** (tests/ohos_platform_test.c, rc=0): 真实验证大缓冲（8 MiB）往返、
   版本宏、blz_depack_safe 对截断/超大 depacked_size 输入拒绝（BLZ_ERROR）与损坏输入写界有界性，
   输出 `ALL brieflz platform tests PASSED`

## 结论

核心库适配（编译/安装/上游测试/消费者验证/鸿蒙专项测试）全部通过；
上游测试全量通过率 10/10 (100%)，无未运行/未实例化项。