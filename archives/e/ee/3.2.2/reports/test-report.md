# 测试报告

> **项目**: ee 3.2.2
> **测试日期**: 2026-09-20
> **测试环境**: HarmonyOS PC aarch64 (OHOS, clang 15.0.4, Conan 2.29.1, profile: ohos-aarch64)
> **测试类型**: 上游测试清点 + HarmonyOS 专项 + 消费者验证 + test_package (L1)

---

## 一、测试摘要

### 上游测试（官方 tag V3.2.2 源码独立用例）

官方包为无构建系统、无测试框架的 STM32 单文件嵌入式库（6 个文件），
经可复制枚举（完整清单见 `reports/upstream-test-ledger.md`）确认：

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 全量发现（source_declared_total） | 0 | N/A |
| 通过 (executed_passed_total) | 0 | N/A |
| 失败 | 0 | N/A |
| 未运行/未实例化 | 0 | N/A |

**全量通过率**: 0/0（上游无测试声明，附清点证据，符合 R51）

### HarmonyOS 专项测试（新增，真实可执行）

| 测试 | 功能 | 结果 |
|------|------|------|
| harmonyos_smoke_test | EE_Init/Capacity/Read/Write/Format 全 API 模拟 Flash 语义验证（写入→回读→格式化→非法参数） | ✅ PASS (rc=0) |

- 源文件: `tests/harmonyos_smoke_test.c`
- 日志: `~/tmp/ee-logs/harmonyos-test-ee-3.2.2.log`
- SHA-256: `a256189207129906a6cc0159e93aa83996349468cb399c0f9c1472f1cd757595`

### 消费者验证用例（独立于上游/鸿蒙专项，真实业务场景）

| 测试 | 功能 | 结果 |
|------|------|------|
| consumer_app_test | 设备参数持久化服务：默认参数初始化→修改→重启回读恢复→格式化清空，全部公开 API（EE_Init/EE_Read/EE_Write/EE_Format/EE_Capacity） | ✅ PASS (rc=0, checks=2) |

- 源文件: `tests/consumer_app_test.c`
- 日志: `~/tmp/ee-logs/consumer-test-ee-3.2.2.log`
- SHA-256: `942c9ffe8151f84778c0438e18081131005c9dbbc76d9ad52dccac0fdef83b52`
- 调用公开 API: EE_Init, EE_Capacity, EE_Read, EE_Write, EE_Format
- 验证结果: 写入值回读一致（light=200 threshold=2048 mode=7 crc=A55A）、格式化后空态

### test_package（L1 官方测试，conan create 内自动执行）

| 测试 | 功能 | 结果 |
|------|------|------|
| test_ee | test.c 内 7 组断言：容量/空态/写回读/格式化/非法参数 | ✅ PASS (conan-verify G2) |

- conan-verify 报告: `reports/conan-verify-report.md`
- W3 本地 CI 模拟: `reports/w3-local-ci.log`（JC/KC 通过，L0-L5 通过）

---

## 二、测试统计口径

- 上游声明总数: **0**（官方包无测试文件/框架/构建系统，附枚举命令与清单）
- 鸿蒙专项: 1 个（新增 `tests/harmonyos_smoke_test.c`）
- 消费者: 1 个（新增 `tests/consumer_app_test.c`，独立计数）
- test_package: 1 个（`test_package/test.c`，7 组断言）

---

## 三、未完成项 / 阻塞

无。所有可运行测试全部通过。
