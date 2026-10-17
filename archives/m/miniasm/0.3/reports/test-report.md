# 测试报告 — miniasm 0.3

> **项目**: miniasm 0.3（命令行工具）
> **测试日期**: 2026-09-15
> **测试环境**: HarmonyOS HongMeng Kernel, aarch64, OHOS clang
> **测试类型**: 消费者功能测试（上游无测试套件，按 R51 自行补充）

---

## 一、测试摘要

| 指标 | 数量 | 百分比 |
|:----:|:----:|:------:|
| 上游测试套件 | 0 | -（上游无） |
| 消费者检查 | 6 | 100% |
| 通过 (PASS) | 6 | 100% |
| 失败 (FAIL) | 0 | 0% |

**核心功能通过率**: **100%**

---

## 二、测试结果

### 2.1 总体评价

✅ **PASS**

### 2.2 消费者测试（6/6）

使用确定性的合成数据（7 条 2500 bp 读段，来自 3600 bp 合成序列）构造 all-vs-all PAF：

| 检查 | 结果 |
|------|------|
| `-V` 输出 `0.3-r179` | ✅ |
| 无参时向 stderr 打印 Usage、返回非 0 | ✅ |
| 输入数据生成（PAF 重叠行） | ✅ |
| `miniasm -f reads.fa reads.paf` 输出 GFA，含 `S` 段 | ✅ |
| `miniasm -p paf reads.paf` 输出重叠记录 | ✅ |
| `miniasm -p bed reads.paf` 正常退出 | ✅ |

### 2.3 上游测试说明

miniasm 0.3 **不提供上游测试套件**：无 `tests/` 目录，Makefile 仅定义
`all`/`miniasm`/`minidot`/`clean`/`depend`，无 `check`/`test` 目标。按 R51
“上游确无测试须附清点证据”，改由本包补充上述端到端功能测试。

### 2.4 已知限制

1. 合成数据的组装结果为冒烟级别验证；未使用真实 PacBio/ONT 数据集（体积大、不属 CI 范畴）。

---

## 三、测试环境

```
OS: HarmonyOS (OHOS) aarch64
Compiler: OHOS clang (Conan profile ohos-aarch64)
Dependencies: zlib/1.3.1 (Conan)
Package: miniasm/0.3 (bin/miniasm + man page)
```

---

*报告生成时间: 2026-09-15*
