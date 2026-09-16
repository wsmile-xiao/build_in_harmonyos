# 测试报告 — minimap 0.2

> **项目**: minimap 0.2（命令行工具 + 静态库）
> **测试日期**: 2026-09-15
> **测试环境**: HarmonyOS HongMeng Kernel, aarch64, OHOS clang
> **测试类型**: 消费者功能测试（上游无测试套件，按 R51 自行补充）

---

## 一、测试摘要

| 指标 | 数量 | 百分比 |
|:----:|:----:|:------:|
| 上游测试套件 | 0 | -（上游无） |
| 消费者检查 | 5 | 100% |
| 通过 (PASS) | 5 | 100% |
| 失败 (FAIL) | 0 | 0% |

**核心功能通过率**: **100%**

---

## 二、测试结果

### 2.1 总体评价

✅ **PASS**

### 2.2 CLI 测试（4/4）

合成 target（2000 bp）与 query（target 的 600 bp 子串）：

| 检查 | 结果 |
|------|------|
| `-V` 输出 `0.2-r123` | ✅ |
| 无参时打印 Usage、返回非 0 | ✅ |
| 直接映射 `target.fa query.fa` 出 hit | ✅ |
| 索引 `-d` 导出 + `-l` 加载映射出 hit | ✅ |

### 2.3 库消费者测试（1/1）

`test_package/test_minimap_consumer.c` 链接安装后的 `libminimap.a` 与头文件
（`minimap.h`/`bseq.h`），调用 `mm_idx_build` + `mm_map`，命中数 > 0，退出码 0。

### 2.4 上游测试说明

minimap 0.2 **不提供上游测试套件**：无 `tests/`，Makefile 仅
`all`/`minimap`/`extra`/`clean`/`depend`。按 R51 附清点证据，改由本包补充测试。

### 2.5 已知限制

1. 使用小型合成数据做冒烟验证；未使用真实基因组数据。

---

## 三、测试环境

```
OS: HarmonyOS (OHOS) aarch64
Compiler: OHOS clang (Conan profile ohos-aarch64)
Dependencies: zlib/1.3.1 (Conan)
Package: minimap/0.2 (bin/minimap + lib/libminimap.a + headers)
```

---

*报告生成时间: 2026-09-15*
