# crc_cpp 1.2.0 测试报告

> **任务号**：crc_cpp-1.2.0-r01-pc2-29-20260922T044311Z
> **测试日期**：2026-09-22
> **测试环境**：HarmonyOS PC OHOS aarch64，Clang 15.0.4，Conan 2.29.1
> **测试命令**：`conan create`（W3）、`build_and_test.sh`（W3 CI 模拟）、`conan-verify crc_cpp 1.2.0`

## 一、上游测试摘要（Catch2）

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| source_declared_total（源码声明 TEST_CASE） | 2 | 100% |
| 实际运行并通过 | 2 | 100% |
| 失败 FAIL | 0 | 0% |
| 未实例化/未运行 | 0 | 0% |
| 断言数 | 47 | — |

**上游结论**：✅ 官方 tag v1.2.0 `test/test.cpp` 声明 2 个独立 TEST_CASE（BitReversing、Algorithm），
OHOS aarch64 clang-15 编译运行 2/2 全部通过（47 assertions），通过率 2/2 = 100.0%。
证据：`reports/upstream-list-tests.log`、`reports/upstream-run.log`、`reports/TEST-LEDGER.md`。

## 二、消费者测试摘要（test_package）

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 消费者用例数 | 2 | 100% |
| 通过 PASS | 2 | 100% |
| 失败 FAIL | 0 | 0% |

**消费者用例**：
- `test.cpp`（test_crc_cpp）：调用公开 API `crc_cpp::crc32/crc16_ccit/crc8` 对 "123456789"
  计算并校验已知向量（0xCBF43926 / 0x29B1 / 0xF4），ALL PASS，exit 0。
- `ohos_special_test.cpp`（test_ohos_special）：HarmonyOS 专项——crc32/crc16_ccit 已知向量 +
  constexpr 编译期计算 static_assert + tiny/small/large 表一致性，ALL PASS，exit 0。

**conan create 输出**：
```
crc_cpp/1.2.0 (test package): RUN: ./test_crc_cpp
crc32("123456789") = 0xCBF43926 expected 0xCBF43926 -> PASS
crc16_ccit("123456789") = 0x29B1 expected 0x29B1 -> PASS
crc8("123456789") = 0xF4 expected 0xF4 -> PASS
test_crc_cpp: ALL PASS (0 fails)
crc_cpp/1.2.0 (test package): RUN: ./test_ohos_special
OHOS-specific test: crc_cpp 1.2.0 on aarch64-linux-ohos (clang 15)
  crc32 known vector: got 0xCBF43926 expected 0xCBF43926 -> PASS
  crc16_ccit known vector: got 0x29B1 expected 0x29B1 -> PASS
  crc32 table-size consistency (tiny/small/large): PASS
RESULT: ALL PASS
```

## 三、验证结果

- conan create（W3）：✅ exit 0（含 test_package 两个消费者二进制）
- conan-verify：✅ G1-G5 全过（配方完整性/干净构建/系统同名库隔离/产物完整性/平台矩阵）
- finish W3 本地 CI（build_and_test.sh，JUNK_PR_DIFF 单包口径）：✅ JC 通过
- manifest 状态：built → 待 publish（submit 阶段制品发布由远端流水线处理）
