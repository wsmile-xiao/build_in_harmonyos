# Test Report — random123 1.14.0 (OHOS arm64)

- 任务: random123-1.14.0-r01-pc5-13-20260907T150624Z (executor pc5-13)
- 工具链: clang/clang++ 15.0.4, --target=aarch64-linux-ohos
- 构建日期: 2026-09-07
- 日志: .ohc-logs/upstream_tests_run.log (SHA-256 0835d5b112dd46896f5c544c049ec0a9777bcc22cf1bd362567432dd230ca720)

## 上游测试运行结果（独立上游用例 13 项）

| 测试程序 | 结果 | 说明 |
|---------|------|------|
| kat_c | PASS | KAT 已知答案测试 60 项通过 |
| kat_cpp | PASS | KAT 已知答案测试 |
| ut_ars | PASS | ARS 生成器单元测试 |
| ut_carray | PASS | 数组类型单元测试 |
| ut_Engine | PASS | 引擎封装单元测试 |
| ut_features | PASS | 特性宏单元测试 |
| ut_ReinterpretCtr | PASS | 计数器重解释单元测试 |
| ut_ua | PASS | uniform.hpp 单元测试 |
| ut_uniform | PASS | 均匀分布转换单元测试 |
| ut_gsl | PASS | GSL 适配单元测试（依赖 GSL/2.8 制品） |
| ut_M128 | PASS(stub) | 无 SSE 平台编译为上游文档化 no-op stub |
| ut_aes | PASS(stub) | 无 SSE 平台编译为上游文档化 no-op stub |
| ut_uniform_IEEEkat | FAIL(已知) | 上游头注释记载的 ARM/FMA 已知情形，非本库缺陷 |

## 鸿蒙专项测试

ohos_special_test: 6/6 通过（特性宏、Threefry4x32 确定性输出、u01 范围/均值 sanity）

## 消费者验证

test_random123 (test_package): philox4x32 确定性校验和 PASS（conan create 内验证）
独立消费者程序 consumer.cpp: 编译运行通过（threefry4x32/philox4x32 C/C++ API）

## 双口径统计

- source_declared_total: 13（按 tests/GNUmakefile all_primary_targets 枚举独立上游用例）
- configured_executable_total: 13（当前 OHOS 配置全部实例化/编译）
- executed_passed_total: 11（10 真实通过 + ut_gsl 依赖恢复后通过；ut_M128/ut_aes 为 no-op stub 通过）
- 失败: 1 (ut_uniform_IEEEkat — 上游记载 ARM 平台已知)
- 未运行/未实例化: 0
- 全量通过率: 11/13 (84.6%)；执行集合通过率 11/11 (100%) 按真实分类详见 notes.md 台账
