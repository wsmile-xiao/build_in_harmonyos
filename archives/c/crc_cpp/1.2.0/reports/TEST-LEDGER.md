# 上游测试台账 — crc_cpp 1.2.0（task crc_cpp-1.2.0-r01-pc2-29）

## 双口径统计

| 口径 | 数值 | 说明 |
|---|---|---|
| source_declared_total | 2 | 官方 tag v1.2.0 `test/test.cpp` 中按可复制枚举规则发现的独立 TEST_CASE 声明数 |
| configured_executable_total | 2 | 当前 OHOS 配置实际实例化/注册的独立可执行用例数（catch2 注册 2 个 test case，同一 tests 可执行文件） |
| executed_passed_total | 2 | 实际执行并通过的用例数 |
| failed_total | 0 | 失败数 |
| uninstantiated_total | 0 | 未实例化/未运行数 |

**全量通过率 = 2/2 (100.0%)**（既即 source 口径全量通过，也即当前配置可执行集合 2/2 通过）。
注意：框架内部宏、模板实例（test_crc 模板对 47 个算法断言）不计为独立用例，仅在断言数中体现（47 assertions）。

## 逐项枚举台账

| 条目 | 类型 | 是否独立上游用例 | 分类理由 | 是否实际运行 | 结果/原因 |
|---|---|---|---|---|---|
| test/test.cpp (TEST_CASE "BitReversing") | 用户测试源 | 是 | 官方 test.cpp 中的独立 TEST_CASE（test_reverse_bits<uint8_t/32/64> 3 个 REQUIRE） | 是 | PASS，见 reports/upstream-run.log |
| test/test.cpp (TEST_CASE "Algorithm") | 用户测试源 | 是 | 官方 test.cpp 中的独立 TEST_CASE（test_crc 模板族对 8/16/32/64 位 44 个算法族断言，共 44 REQUIRE + 2 前置 REQUIRE） | 是 | PASS，见 reports/upstream-run.log |
| test/CMakeLists.txt | 构建目标/注册清单 | 否 | 仅注册 tests 可执行文件与 CATCH_DISCOVER_TESTS；非用例本身 | 不适用 | 构建目标定义，未独立计数 |
| test.cpp 内 test_crc/constexpr_check_message 模板 | 框架辅助函数 | 否 | 辅助模板，展开为断言而非独立用例 | 不适用 | 在 "Algorithm" 内执行（47 assertions 含 constexpr static_assert） |
| static_assert(constexpr_test_result) | 编译期断言 | 否 | 编译期检查，非运行用例 | 编译期已执行 | 编译通过即成立 |
| include/crc_cpp.h | 框架头/被测库源码 | 否 | 被测库头文件，非测试声明 | 不适用 | — |
| cmake/、.github/workflows/ | 构建框架/CI | 否 | 构建配置与 CI 脚本，非测试用例 | 不适用 | — |
| README.md 中的示例 | 样例 | 否 | 文档示例，非独立测试声明 | 不适用 | — |

## 逐项映射（源码声明 → 构建目标 → 注册 → 实际执行）

1. `TEST_CASE("BitReversing","TestHelperFunction")`（test/test.cpp:88）
   → 编译目标 `tests`（test/CMakeLists.txt ADD_EXECUTABLE）
   → catch2 注册项 `BitReversing`
   → 实际执行：`crc_upstream_tests` 运行日志 "All tests passed (47 assertions in 2 test cases)"，确认 2/2 ✓
2. `TEST_CASE("Algorithm","TestCRC")`（test/test.cpp:95）
   → 编译目标 `tests`
   → catch2 注册项 `Algorithm`
   → 同上实际执行 ✓

## 运行证据

- 枚举：`reports/upstream-list-tests.log`（--list-tests：BitReversing / Algorithm，2 test cases）
- 运行：`reports/upstream-run.log`（All tests passed, 47 assertions in 2 test cases, exit 0）
- 编译命令：`clang++ -std=c++20 -I <src>/include -I <catch2-3.8.1-ohos>/include test/test.cpp <catch2>/lib/libCatch2Main.a <catch2>/lib/libCatch2.a -o crc_upstream_tests`
- 依赖查询：catch2/3.2.1（上游 CMakeLists 声明）在 ohpcd registry 0 匹配；catch2/3.8.1 在本地缓存与 ohpcd 均可用（ohos armv8 Release clang15 libc++），采用 3.8.1。

## 鸿蒙专项测试

- 源：`ohos_crc_test.cpp`（本任务新增，独立于上游测试）
- 编译命令：`clang++ -std=c++20 -I <src>/include ohos_crc_test.cpp -o ohos_crc_test`
- 运行输出：
  - crc32 known vector: got 0xCBF43926 expected 0xCBF43926 -> PASS
  - crc16_ccit known vector: got 0x29B1 expected 0x29B1 -> PASS
  - crc32 table-size consistency (tiny/small/large): PASS
  - RESULT: ALL PASS, exit 0
- 覆盖：公开 API（crc_cpp::crc32/crc16_ccit/crc8、family/crc32、table_size）调用及其可观察结果；constexpr 编译期计算 static_assert；tiny/small/large 表一致性。