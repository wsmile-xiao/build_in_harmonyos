# qrencode 4.1.1.1 测试报告（上游 4.1.1）

> 测试日期: 2026-09-04
> 测试环境: Windows 本地 Conan/MinGW + HarmonyOS PC aarch64 真机
> 测试类型: 上游 CTest、Conan 消费者测试、OHOS 真机测试

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 上游测试组 | 12 | 100% |
| 通过 (PASS) | 12 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**上游核心功能通过率**: **100%**

消费者测试另计 `1/1` PASS；本地 Conan 上游 CTest 入口另计 `3/3` PASS。

## 二、测试结论

### 2.1 总体评价

Conan 修订 `4.1.1.1` 的库配方、本地上游 CTest `3/3` 和真实消费者 API `1/1` 均通过；OHOS 真机 `12/12 + 1/1` 为同一上游 `v4.1.1` 源码的历史等价事务，保留其身份边界而不冒充新的真机 launch。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 可选 PNG 后端未启用 | 默认构建不提供 PNG 输出 | 低 |
| 上游 CMake minimum 较旧 | 需要设置 CMAKE_POLICY_VERSION_MINIMUM=3.5 | 低 |

### 2.3 可用功能清单

```
PASS: QR 编码核心库
PASS: QRcode_encodeString 消费者 API
PASS: 上游 12 个真机测试程序
PASS: 静态库安装与 Conan test_package
LIMITED: PNG 工具和 PNG 输出默认关闭
```

### 2.4 已知限制

1. 默认 `without_png=True`，PNG 相关功能需显式开启并提供依赖。
2. 默认静态库配置不验证 OHOS shared-object 签名路径。

## 三、测试详情

### 3.1 通过的测试

| 测试项 | 功能 | 结果 |
|--------|------|------|
| test_bitstream | 位流操作 | PASS |
| test_estimatebit | 位数估算 | PASS |
| test_split | 输入分割 | PASS |
| test_qrinput | QR 输入编码 | PASS |
| test_qrspec | QR 规格与帧 | PASS |
| test_mqrspec | Micro QR 规格 | PASS |
| test_qrencode | QR 编码主流程 | PASS |
| test_split_urls | URL 分割 | PASS |
| test_monkey | 随机编码 | PASS |
| test_mask | 掩码评估 | PASS |
| test_mmask | Micro QR 掩码 | PASS |
| test_rs | Reed-Solomon | PASS |
| consumer | `QRcode_encodeString` API | PASS |

### 3.2 失败的测试

无。测试日志中每项 `TEST_RC` 均为 0。

### 3.3 跳过的测试

无。PNG 工具不是跳过的测试项，而是由冻结的 `WITH_TOOLS=OFF` 和 `WITHOUT_PNG=ON` 配置排除。

## 四、关键问题分析

### CMake 可选后端导致测试分母漂移

**现象**：不同主机自动发现 PNG、Iconv 后会生成不同数量的测试目标。

**根因分析**：上游 CMakeLists.txt 通过 `WITH_TOOLS`、`WITHOUT_PNG`、`WITH_TESTS` 和 `find_package` 条件创建目标，宿主依赖差异会改变 CTest 清单。

**解决方案**：在 Conan `CMakeToolchain` 中显式设置开关；配置后从同一构建树读取清单并执行。知识草稿为 `E2175`。

## 五、测试环境

```
上游: libqrencode v4.1.1
源码 SHA-256: 5385bc1b8c2f20f3b91d258bf8ccc8cf62023935df2d2676b5b67049f31a049c
本地: Conan 2.29.1, MinGW/GCC 15.2.0, CMake 4.4.0
真机: 10.62.150.125:8022, boot 068fec8d-10f6-40f7-93a6-9153e0ad6d33
真机事务: qrencode-4.1.1-w3-20260904-004
真机证据: F:\HarmonyPC\miniupnpc-2.3.11-adapt-20260904\w3-successor-20260904-r4
```

## 六、证据绑定

- 真机上游日志 SHA-256: `b98daeb1b9ad64a4b91ffb525acae6a0ac2a08f2d24247df0d92ddf8b5d2e69b`
- 真机冻结结果: `result-frozen.json`，声明 `upstream=12/12`、`consumer=PASS`、`launch_count=1`
- 新修订本地 CI：`archives/q/qrencode/4.1.1.1/.ci-result.json`，`exit_code=0`，integrity `a88ca8cad5a54964`
- 新修订本地构建日志：`archives/q/qrencode/4.1.1.1/reports/conan-create.log` 与任务私有 `direct-w3-ninja2-20260904.log`
