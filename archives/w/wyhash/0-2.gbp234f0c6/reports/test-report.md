# 测试报告 — wyhash 0-2.gbp234f0c6

> **项目**: wyhash 0-2.gbp234f0c6 (header-only)
> **测试日期**: 2026-09-15
> **测试环境**: HarmonyOS HongMeng Kernel, aarch64, OHOS clang
> **测试类型**: 上游官方测试 (test_vector.cpp) + 消费者测试 (test_wyhash.cpp)

---

## 一、测试摘要

| 指标 | 数量 | 百分比 |
|:----:|:----:|:------:|
| 上游测试程序 | 1 | 100% |
| 通过 (PASS) | 1 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 消费者断言 | 22 | 100% |
| 消费者检查通过 | 22 | 100% |

**核心功能通过率**: **100%**

---

## 二、测试结果

### 2.1 总体评价

✅ **PASS**

### 2.2 测试详情

**层 1 — 上游官方测试** `test_package/conanfile.py::_run_upstream_tests`

- 下载锁定提交的源码快照（commit `234f0c6`，sha256 校验通过）。
- 编译并运行上游 `test_vector.cpp`，stdout 与提交的 7 行基线逐字节一致：

| 向量 | 结果 |
|------|------|
| `wyhash("",0)` | ✅ 0x42bc986dc5eec4d3 |
| `wyhash("a",1)` | ✅ 0x84508dc903c31551 |
| `wyhash("abc",2)` | ✅ 0x0bc54887cfc9ecb1 |
| `wyhash("message digest",3)` | ✅ 0xadc146444841c430 |
| `wyhash("abcdefghijklmnopqrstuvwxyz",4)` | ✅ 0x4c0977bd4f14f34a |
| `wyhash("ABC…789",5)` | ✅ 0x6f8bd609a8a276d2 |
| `wyhash("1234…7890",6)` | ✅ 0x498d7c21668259ad |

**层 2 — 消费者测试** `test_package/test_wyhash.cpp`（22 项检查全部通过）

- 7 个官方向量
- `wyhash64` 4 项
- `wyrand` 5 项（含种子推进）
- `wy2u0k` 2 项
- >64 字节累积路径 2 项（200 字节、300 字节）
- `wy2u01` / `wy2gau` 取值范围 2 项

### 2.3 已知限制

1. 哈希值绑定上游快照 `234f0c6`；上游 final-4 版本结果不同。

---

## 三、测试环境

```
OS: HarmonyOS (OHOS) aarch64
Compiler: OHOS clang (Conan profile ohos-aarch64, compiler.version=15)
Package: wyhash/0-2.gbp234f0c6 (header-only)
```

---

*报告生成时间: 2026-09-15*
