# 测试报告 — libbiosoup-dev 0.11.0

> **项目**: libbiosoup（biosoup，header-only C++）
> **测试日期**: 2026-09-15
> **测试环境**: HarmonyOS HongMeng Kernel, aarch64, OHOS clang
> **测试类型**: 消费者 API 测试（上游 GoogleTest 套件不可在 CI 运行）

---

## 一、测试摘要

| 指标 | 数量 | 百分比 |
|:----:|:----:|:------:|
| 上游测试套件 | 0 运行 | 需 GoogleTest，CI 不可用 |
| 消费者检查 | 14 | 100% |
| 通过 (PASS) | 14 | 100% |
| 失败 (FAIL) | 0 | 0% |

**核心功能通过率**: **100%**

---

## 二、测试结果

### 2.1 总体评价

✅ **PASS**

### 2.2 消费者测试（14/14）

`test_package/test_biosoup.cpp`（期望值取自上游 GoogleTest 用例，去掉 gtest）：

| 检查 | 结果 |
|------|------|
| 非核苷酸输入抛 `std::invalid_argument` | ✅ |
| `NucleicAcid::Code(i)` 2-bit 编码值 | ✅ |
| `InflateData()` 全量与子串（含越界返回空串） | ✅ |
| `Sequence::ReverseAndComplement()` 数据与质量分 | ✅ |
| `Overlap` 字段与 cigar | ✅ |
| `Timer::Start/Stop` 非负 | ✅ |

### 2.3 上游测试说明

上游 `test/` 有 5 个 GoogleTest 用例文件，gtest 通过 meson subproject（`gtest.wrap`）
引入，CI 不具备；MANIFEST 中如实声明跳过，并在 test_package 复用其期望值。

### 2.4 已知限制

1. 未运行上游 GoogleTest 套件（依赖不可用）；已复用其期望值覆盖核心 API。

---

## 三、测试环境

```
OS: HarmonyOS (OHOS) aarch64
Compiler: OHOS clang (Conan profile ohos-aarch64)
Package: libbiosoup-dev/0.11.0 (header-only)
```

---

*报告生成时间: 2026-09-15*
