# Test Report — lwprintf 1.1.0 (OHOS aarch64)

## 测试概览

| 项目 | 结果 |
|------|------|
| 库构建 (conan create, OHOS arm64) | ✅ 通过 (G2, exit 0) |
| test_package 消费者测试 | ✅ 通过 (conan create 内运行, 2 断言) |
| 上游测试 (tests/test.c, LwLibPROJECT) | ✅ 已实跑: 148 通过 / 3 失败 / 151 执行 (详见 upstream-test-ledger.md) |
| OhOS 专项测试 | ✅ 13/13 断言通过 (ohos-tests/ohos_specific_test.c, exit 0) |
| 消费者用例 (日志模块) | ✅ 通过 (consumer-tests/consumer_log_module.c, exit 0) |
| conan-verify 门禁 | ✅ G0/G1/G2/G3/G4 全 PASS |

## 测试细节

- 上游测试: `$HOME/oh-downloads/lwprintf-testbuild` 下 OHOS 工具链编译 LwLibPROJECT 并运行；
  148/151 = 98.0% 可执行集合通过率；全量声明 170 条口径 148/170 = 87.1%（3 项 %p 32 位指针假设失败 + 19 项上游 #if 0 禁用）。
  完整台账与逐项映射见 `reports/upstream-test-ledger.md`。
- OhOS 专项测试: `archives/l/lwprintf/1.1.0/ohos-tests/ohos_specific_test.c`（自定义实例隔离、%*K 字节数组、截断语义、64 位 %p、int64/uint64），13/13 通过。
- 消费者用例: `archives/l/lwprintf/1.1.0/consumer-tests/consumer_log_module.c`（模拟业务日志组件，调用 lwprintf_init_ex/lwprintf_snprintf_ex/lwprintf_printf_ex），exit 0。

## 测试统计（双口径）

- `source_declared_total` = 170（tests/test.c 内 do_test 声明总数）
- `configured_executable_total` = 151（#if 0 禁用 19 项后的活动断言）
- `executed_passed_total` = 148
- `failed_total` = 3（%p 32 位指针假设，OHOS arm64 为 64 位指针）
- 全量通过率 148/170 = 87.1%；可执行集合通过率 148/151 = 98.0%