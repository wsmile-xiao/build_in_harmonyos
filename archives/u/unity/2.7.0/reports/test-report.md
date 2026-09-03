# Unity 2.7.0 测试报告（OHOS aarch64）

- 平台：OpenHarmony PC aarch64，clang-15（/data/service/hnp/bin/clang），C standard=gnu99
- 被测库：libunity.so（`clang -std=gnu99 -fPIC -shared -O2 -Isrc -D UNITY_INCLUDE_DOUBLE -D UNITY_SUPPORT_64 src/unity.c`）
- 上游测试：官方 `test/` 自检套件，`make -C test CC=clang CFLAGS='-O2' test`（8 个 runner，awk 生成，零上游源码修改）
- 执行日期：2026-09-03

## 汇总

| 指标 | 数量 |
|---|---|
| 总测试数 | 872 |
| 通过 PASS | 869 |
| 失败 FAIL | 0 |
| 跳过 SKIP | 3 |

## 上游套件明细（本机 OHOS aarch64 实跑，2026-09-03）

| 套件 | 总 | 通过 | 失败 | 跳过 |
|---|---|---|---|---|
| arrays | 274 | 274 | 0 | 0 |
| core | 26 | 26 | 0 | 0 |
| doubles | 101 | 101 | 0 | 0 |
| floats | 102 | 99 | 0 | 3 |
| integers | 258 | 258 | 0 | 0 |
| integers_64 | 55 | 55 | 0 | 0 |
| memory | 14 | 14 | 0 | 0 |
| strings | 42 | 42 | 0 | 0 |
| **合计** | **872** | **869** | **0** | **3** |

## 3 个跳过（SKIP/IGNORE）的具体技术原因

上游 Unity v2.7.0 的 **floats 套件**中 3 个用例按上游设计条件性跳过，非适配问题：

- 跳过的用例：`testFloatPrinting`、`testFloatPrintingRoundTiesToEven`、`testFloatPrintingRandomSamples`（均为 `TEST_ASSERT_PRINT_FLOAT` 系列浮点数**打印格式**断言）
- 触发点：`test/tests/test_unity_floats.c:1211`（及 1263、1287 行同款守卫）：
  `#if defined(UNITY_EXCLUDE_FLOAT_PRINT) || defined(UNITY_INCLUDE_DOUBLE) || !defined(USING_OUTPUT_SPY)` → `TEST_IGNORE()`
- 根因：上游 `test/Makefile` 的 `DEFINES` 自带 `-D UNITY_INCLUDE_DOUBLE`，此时 `TEST_ASSERT_PRINT_FLOAT` 走 double 输出路径，float 打印 spy 无法拦截其输出，上游源码即主动 `TEST_IGNORE()` 这 3 个用例——是上游测试框架对 `UNITY_INCLUDE_DOUBLE` 构建模式的既定行为，与 OHOS 平台无关
- 复现证据：本机（OHOS aarch64，clang-15，与 CI worker 同平台）实跑 `make -C test CC=clang CFLAGS='-O2' test`，floats 套件输出 `102 Tests 0 Failures 3 Ignored`，3 个 IGNORE 行即上述 3 用例名

## 失败 FAIL

无（0 失败）。

## 已知限制

1. 3 个 floats 打印用例在上游 `UNITY_INCLUDE_DOUBLE` 默认构建下恒被跳过；若需覆盖，须以 `-DUNITY_EXCLUDE_DOUBLE -UUNITY_INCLUDE_DOUBLE` 单独构建 floats runner（上游 Makefile 默认配置不含此组合，不在本次适配范围）
2. 上游 runner 为 awk 脚本生成（`test/UnityTestRunnerGenerator/`），无 ruby 依赖，OHOS 上原生可运行

## 结论

✅ 通过（869/872 PASS，0 FAIL，3 个 SKIP 为上游设计性条件跳过，已定位到源码行）
