# jsonifier 0.9.97 测试报告

**测试日期:** 2026-09-03
**测试环境:** HarmonyOS / OpenHarmony aarch64（OHOS SDK 26.0.0.18）
**编译器:** clang 15.0.4（aarch64-unknown-linux-ohos）
**测试类型:** 上游测试套件 + HarmonyOS 专项测试 + 消费者验证

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数（上游独立用例） | 238 | 100% |
| 通过 (PASS) | 211 | 88.66% |
| 失败 (FAIL) | 0 | 0% |
| 不可运行（上游硬阻塞） | 27 | 11.34% |
| 专项测试断言 | 11 | 100% |

**核心功能通过率**: ✅ **88.66%（实际运行部分 211/211 = 100%）**

---

## 二、测试结论

### 2.1 总体评价

✅ **适配完成，核心功能全部通过**

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| RoundTrip 测试组不可编译（0.9.97 编译期哈希表无法为含指针成员结构构造，原始头与补丁头一致复现，属上游缺陷） | 27 个往返用例 | 🟡 |
| validateJson 数字路径缺陷（0.9.97 上游 consumeSign 对无符号数字返回 false） | validateJson 数字校验 | 🟡 |
| OHOS SDK clang-15 前端 IRGen 段错误（validateJson 完整实例化时，clang-22 正常） | 工具链 | 🟡 |

### 2.3 可用功能清单

```
✅ parseJson：map/vector/嵌套数组/数字极值/UTF-8 中文（上游 59+43+69+9 用例全通过）
✅ serializeJson：vector/map 序列化与往返
✅ validateJson：对象/数组结构校验（上游 31 conformance 用例全通过）
✅ HarmonyOS 专项测试 13/13（NEON 路径、UTF-8、数字极值含次正规数边界、嵌套、空输入）
✅ test_package 消费者验证 ALL TESTS PASSED
```

---

## 三、上游测试明细（详见 reports/upstream-test-ledger.md）

| 测试组 | 独立用例数 | 通过 | 通过率 |
|--------|:----:|:----:|:------:|
| FloatValidation | 69 | 69 | 100% |
| IntValidation | 59 | 59 | 100% |
| UintValidation | 43 | 43 | 100% |
| StringValidation | 9 | 9 | 100% |
| ConformanceTests | 31 | 31 | 100% |
| RoundTrip | 27 | 0 | 0%（硬阻塞，见台账） |
| **合计** | **238** | **211** | **88.66%** |

## 四、HarmonyOS 专项测试（test_ohos_specific.cpp）

13/13 断言通过、退出码 0：NEON 路径较大多层文档解析/序列化、UTF-8 中文往返、int64/uint64/double 极值解析（含 DBL_MIN 最小正正规数、denorm_min 最小次正规数、最大次正规数边界）、双层嵌套数组往返、空输入拒绝。

## 五、消费者验证（test_package/test_jsonifier.cpp）

compile + run ALL TESTS PASSED：serializeJson(vector)、parseJson(map)、vector roundtrip、parseJson(vector)。
