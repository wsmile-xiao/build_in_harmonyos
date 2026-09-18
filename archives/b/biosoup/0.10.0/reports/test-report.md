# 测试报告 — biosoup 0.10.0（OHOS aarch64）

- 日期: 2026-09-18
- 环境: 鸿蒙 PC 真机，clang 15.0.4（aarch64-unknown-linux-ohos），conan 2.29.1，profile ohos-aarch64
- 验证: conan-verify G0–G4 / L2 / L4 / L5 全部 PASS；W3 L1 = upstream tests + test_package executed

## 测试账本（五维）

| 维度 | 数值 | 说明 |
|------|------|------|
| N_static（上游静态用例） | 11 | gtest TEST 定义逐条计数：nucleic_acid_test 4、overlap_test 1、progress_bar_test 1、sequence_test 1、timer_test 4 |
| N_registered（构建系统注册） | 1 | ctest 注册 biosoup_test（承载全部 11 个 gtest 用例） |
| N_executed（实际执行） | 11 | `[==========] 11 tests from 5 test suites ran.` `[  PASSED  ] 11 tests.` |
| 未执行分类数 | 0 | 无条件编译互斥、无资源缺失跳过 |
| N_consumer（消费者测试） | 1 | test_package/test_biosoup.cpp，4 断言 |

## 上游测试执行证据（conan create，ctest 驱动）

```text
Test project /storage/Users/currentUser/tmp/ch/home-glm50-biosoup/p/b/bioso1ef93a3e1752f/b/build/Release
1/1 Test #1: biosoup_test .....................   Passed    2.40 sec
100% tests passed, 0 tests failed out of 1
Total Test time (real) =   2.41 sec
```

gtest 逐用例统计（直接执行 biosoup_test 复核）：

```text
[----------] 4 tests from BiosoupTimerTest (2349 ms total)
[==========] 11 tests from 5 test suites ran. (2350 ms total)
[  PASSED  ] 11 tests.
```

## 消费者测试（test_package）

```text
biosoup consumer test PASS
```

- 程序：test_biosoup（真实编译、链接 header-only 库）
- 断言：①Sequence 构造 name/data 落位 ②num_objects 原子唯一 id ③quality 字段 ④ReverseAndComplement 语义（ACGTT→AACGT）

## 结论

上游测试 11/11 通过（100%，分母=静态全量），消费者测试 1/1 通过（4 断言），无跳过项，无伪造。
