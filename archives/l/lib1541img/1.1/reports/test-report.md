# 测试报告 — lib1541img 1.1

> **项目**: lib1541img 1.1（C 静态库）
> **测试日期**: 2026-09-15
> **测试环境**: HarmonyOS HongMeng Kernel, aarch64, OHOS clang
> **测试类型**: 消费者端到端测试（上游无测试套件）

---

## 一、测试摘要

| 指标 | 数量 | 百分比 |
|:----:|:----:|:------:|
| 上游测试套件 | 0 | -（上游无） |
| 消费者检查 | 25 | 100% |
| 通过 (PASS) | 25 | 100% |
| 失败 (FAIL) | 0 | 0% |

**核心功能通过率**: **100%**

---

## 二、测试结果

### 2.1 总体评价

✅ **PASS**

### 2.2 消费者测试（25/25）

`test_package/test_1541img.c`：链接安装后的 `lib1541img.a`，通过公开 API 完成一个完整流程：

| 阶段 | 检查 |
|------|------|
| 物理层 | `D64_create(D64_STANDARD)`、`D64_tracks()==35` |
| 文件系统 | `CbmdosFs_create(CFO_DEFAULT)`、`CbmdosFs_status()==CFS_OK`、`CbmdosVfs` 可用 |
| 文件 | `FileData_append`、`CbmdosFile_setType/setName/setData`、`CbmdosVfs_append` |
| 写盘 | `writeD64` 写出 `.d64` |
| 读回 | `readD64` + `CbmdosFs_fromImage`；校验文件数、名字、类型、内容 |

### 2.3 上游测试说明

上游无测试套件：发布包无 `tests/`，构建依赖 `zimk` 子模块（GNU make 框架），
Makefile 也无 `check`/`test` 目标。按 R51 附清点证据，改由本包补充端到端测试。

### 2.4 已知限制

1. 未运行上游（无）测试；端到端覆盖建盘、加文件、写盘、读回。

---

## 三、测试环境

```
OS: HarmonyOS (OHOS) aarch64
Compiler: OHOS clang (Conan profile ohos-aarch64)
Package: lib1541img/1.1 (lib/lib1541img.a + include/1541img/*.h)
```

---

*报告生成时间: 2026-09-15*
