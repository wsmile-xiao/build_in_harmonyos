# 测试报告 — units-cpp 2.3.4

> **项目**: units-cpp 2.3.4（header-only C++14 单位换算库）
> **测试日期**: 2026-09-17
> **测试环境**: HarmonyOS / OHOS aarch64, OHOS clang 15 (Conan profile `ohos-aarch64`)
> **测试类型**: 上游 GoogleTest 套件 + 消费者 API 测试

---

## 一、测试摘要

| 指标 | 数量 | 百分比 |
|:----:|:----:|:------:|
| 上游测试用例（注册） | 188 | — |
| 上游实际运行 | 186 | 98.9% |
| 上游通过 | 186 | 100%（已运行项） |
| 上游失败 | 0 | 0% |
| 上游排除 | 2 | 见 2.3 |
| 消费者检查（test_package） | 20 | 100% |
| 消费者通过 | 20 | 100% |
| 失败合计 | 0 | 0% |

**核心结论**: 编译通过；`conan create` 退出码 0；上游已运行用例 100% 通过，消费者 20/20 通过。

---

## 二、测试结果

### 2.1 总体评价

✅ **PASS**

### 2.2 上游测试（186/188，186 通过）

上游 `unitTests/main.cpp` 实测注册 188 个 `TEST_F`：

```
unitTests/unitLibTest --gtest_list_tests | grep -c '^  '   # -> 188
unitTests/unitLibTest --gtest_filter=-UnitContainer.to_string_locale:UnitContainer.cout
# [==========] 186 tests from 9 test suites ran. (7 ms total)
# [  PASSED  ] 186 tests.
```

| 测试套件 | 用例数 | 结果 |
|----------|:------:|------|
| TypeTraits | 47 | ✅ |
| UnitManipulators | 5 | ✅ |
| UnitContainer | 26（注册 28，排除 2） | ✅ |
| UnitConversion | 38 | ✅ |
| UnitMath | 38 | ✅ |
| Constexpr | 5 | ✅ |
| CompileTimeArithmetic | 9 | ✅ |
| CaseStudies | 2 | ✅ |
| UnitLimits | 16 | ✅ |

### 2.3 排除的 2 项（平台环境差异，非库缺陷）

| 用例 | 原因 |
|------|------|
| `UnitContainer.to_string_locale` | 断言 `setlocale(LC_ALL, "de_DE.utf8")` / `en_US.utf8` 成功；OHOS bionic 不提供 locale 数据，`setlocale` 返回 NULL |
| `UnitContainer.cout` | 使用 gtest `CaptureStdout`，其临时文件路径在 googletest 1.12.1 中硬编码为 `/tmp`；真机 `/tmp` 属 root 且普通用户只读，`mkstemp` 失败并触发 SIGABRT |

二者均已如实记入 `test_package/MANIFEST.yml` 与版本级 `manifest.yaml`。

### 2.4 消费者测试（20/20）

`test_package/test_units.cpp` 通过安装后的包（CMakeDeps + `find_package(units)`、`units::units`）编译运行：

| 检查 | 结果 |
|------|------|
| 长度换算 m→ft（3.28084）、km→m（1000）、mi→m（1609.344） | ✅ |
| 用户定义字面量 `2.5_m`、`1_km` | ✅ |
| 仿射温度 C↔F（100℃=212℉，32℉=0℃） | ✅ |
| 质量 kg→g（1000）、时间 min→s（60） | ✅ |
| 十进制/二进制数据单位 byte/bit（8）、kB（1000）、KiB（1024） | ✅ |
| 能量 kJ→J（1000）、功率 kW→W（1000） | ✅ |
| 复合速度 m/s→km/h（3.6） | ✅ |
| 容器算术 2m+3m=5m | ✅ |
| `to_string(meter_t(8)) == "8 m"` | ✅ |
| `unit_cast<double>` | ✅ |
| `std::chrono` 双向互操作（second_t↔nanoseconds） | ✅ |

### 2.5 已知限制

1. 上游 2 项平台相关用例未运行（见 2.3），已在 MANIFEST 中逐条说明。

---

## 三、测试环境

```
OS: HarmonyOS (OHOS) aarch64
Compiler: OHOS clang 15.0.4 (Conan profile ohos-aarch64)
Package: units-cpp/2.3.4 (header-only)
Upstream tests: GoogleTest 1.12.1 (bundled 3rdParty/gtest/googletest-1.12.1.zip)
```

---

*报告生成时间: 2026-09-17*
