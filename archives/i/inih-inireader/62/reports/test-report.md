# 测试报告 — inih-inireader 62

> **项目**: inih-inireader 62 (inih r62 + INIReader)
> **测试日期**: 2026-09-15
> **测试环境**: HarmonyOS HongMeng Kernel, aarch64, OHOS clang
> **测试类型**: 上游官方测试 (unittest.sh + INIReader examples) + 消费者测试

---

## 一、测试摘要

| 指标 | 数量 | 百分比 |
|:----:|:----:|:------:|
| 上游测试用例 | 17 | 100% |
| 通过 (PASS) | 17 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 消费者断言 | 13 | 100% |
| 消费者检查通过 | 13 | 100% |

**核心功能通过率**: **100%**

---

## 二、测试结果

### 2.1 总体评价

✅ **PASS**

### 2.2 上游官方测试（17/17）

C 解析器 — `tests/unittest.sh` 的 15 组编译/运行变体，输出与 `baseline_*.txt` 逐字节一致：

| 用例 | 结果 | 用例 | 结果 |
|------|------|------|------|
| multi | ✅ | heap_max_line | ✅ |
| multi_max_line | ✅ | heap_realloc | ✅ |
| single | ✅ | heap_realloc_max_line | ✅ |
| disallow_inline_comments | ✅ | heap_string | ✅ |
| stop_on_first_error | ✅ | call_handler_on_new_section | ✅ |
| handler_lineno | ✅ | allow_no_value | ✅ |
| string | ✅ | alloc | ✅ |
| heap | ✅ | | |

C++ 封装 — `examples/`：

| 用例 | 基线 | 结果 |
|------|------|------|
| INIReaderExample | `cpptest.txt` | ✅ |
| INIReaderExampleErrors | `cpptesterrors.txt` | ✅ |

### 2.3 消费者测试（13/13）

`test_package/test_inih_inireader.cpp`，通过安装后的包链接两个静态库：

- C API：`ini_parse_string` 返回 0、回调 4 次、section/name/value 正确；
- C++ API：`ParseError`、`Get`、`GetInteger`、`GetReal`、`GetBoolean`、
  默认值、`HasSection`（真/假）、`HasValue`、`Keys` 计数。

### 2.4 已知限制

1. 无（上游在 OHOS/aarch64 上直接可编译，无需补丁）。

---

## 三、测试环境

```
OS: HarmonyOS (OHOS) aarch64
Compiler: OHOS clang (Conan profile ohos-aarch64)
Package: inih-inireader/62 (static libinih.a + libINIReader.a)
```

---

*报告生成时间: 2026-09-15*
