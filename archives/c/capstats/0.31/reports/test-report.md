# capstats 0.31 测试报告

> **任务号**：6198
> **测试日期**：2026-09-06
> **测试环境**：HarmonyOS PC OHOS aarch64，Clang 15.0.4，Conan 2.29.1
> **测试命令**：`conan-verify capstats 0.31`、W3 `build_and_test.sh archives/c/capstats/0.31`

## 一、上游测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 0 | N/A |
| 通过 PASS | 0 | N/A |
| 失败 FAIL | 0 | N/A |
| 跳过 SKIP | 0 | N/A |

**上游结论**：✅ 源码静态没有测试声明，实际执行数为 0；配方真实执行 CTest，日志为 `No tests were found!!!`。这不是把消费者测试计入上游测试。

## 二、消费者测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 1 | 100% |
| 通过 PASS | 1 | 100% |
| 失败 FAIL | 0 | 0% |
| 跳过 SKIP | 0 | 0% |

**消费者结论**：✅ `test_package/test.sh` 运行 `capstats --version 2>&1`，断言输出为 `capstats 0.31`，1/1 通过。

## 三、验证详情

| 验证项 | 结果 | 原始证据 |
|---|---|---|
| CMake configure | PASS | 找到 `libpcap.a`，配置完成 |
| 编译与安装 | PASS | 生成并安装 `bin/capstats` |
| 上游 CTest | PASS（空套件） | `ctest --test-dir ... --output-on-failure`；`No tests were found!!!` |
| Conan test_package | PASS | `capstats --version => capstats 0.31` |
| W3 L1e 反向复核 | PASS | 移走 `bin/` 后测试不能绕过被测产物 |
| W3 产物检查 L2/L4/L5 | PASS | `capstats --version`、补丁扫描、bin 基线均通过 |

## 四、已知限制

1. 上游 0.31 未提供自动化测试，因此上游执行/通过计数均为 0；消费者测试单独统计为 1/1。
2. finish 的 legacy G0 clean-verify 不注入 Conan 依赖，直接运行源码 `configure` 时无法找到 libpcap；正式 Conan G2 和 W3 使用已发布 `libpcap/1.10.6`，均已通过。

## 五、产物验证

| 产物 | 结果 | 验证 |
|---|---|---|
| `bin/capstats` | PASS | Conan G4 与 W3 L5 检查存在并可运行 |
| `capstats --version` | PASS | 返回 `capstats 0.31` |
| `capstats-0.31-ohos-aarch64.tar.gz` | PASS | PackageBuilder 生成，包含 release 产物 |
| `capstats-0.31-ohos-aarch64-debug.tar.gz` | PASS | PackageBuilder 生成，包含调试符号 |
