# 测试报告 — fmi-ls-bus 1.0.0

**日期**: 2026-09-22
**执行端**: pc7-14（worktree `feat/fmi-ls-bus-1.0.0`）
**编译器**: clang/clang++ 15.0.4（OHOS aarch64，`-std=c++17`）
**测试依赖**: gtest/1.17.0.2（ohpcd registry 预编译包）

## 一、上游测试（源码声明 → 可实例化 → 实际执行 逐项映射）

### 枚举口径
- 官方 v1.0.0 发布版 `tests/` 含 2 个用户测试源文件，共 **234 个独立 TEST 用例**：
  - `tests/test/fmi_3_ls_bus_header_tests_can.cpp` — 130 个 `TEST(...)`
  - `tests/test/fmi_3_ls_bus_header_tests_flexray.cpp` — 104 个 `TEST(...)`
- 测试助手（`tests/helper/`）4 个文件：仅为断言辅助函数，无 TEST 宏，不计独立用例
- 框架头：`fmi3PlatformTypes.h`（官方 fmi-standard）+ GTest——框架非用例
- 样例/基准/fixture/脚本：无独立 benchmark/fixture/pytest；唯一构建目标 `fmi_3_ls_bus_header_test`
- SECTION 子节：0（两文件均无 SECTION）

### 实例化与执行映射
| 源码声明（TEST 数） | 预处理/构建条件 | 构建目标 | ctest 注册 | 实际执行 |
|---|---|---|---|---|
| can 130 | CMake `MODULE_LIST=can`（v1.0.0 发布版唯一含头的模块） | `fmi_3_ls_bus_header_test` | 130（ctest -N Total Tests: 130） | **130/130 Passed** |
| flexray 104 | v1.0.0 发布版 headers/ 不含 `fmi3LsBusFlexRay.h`/`fmi3LsBusUtilFlexRay.h`（main 与 v1.1.0-beta.2 才有）→ 明确上游排除条件 | — | 0（MODULE_LIST=all 构建失败：`fatal error: 'fmi3LsBusFlexRay.h' file not found`，BUILD_ALL_EXIT:2） | 未实例化 |

### 双口径统计（最终）
- **全量口径**：`executed_passed_total / source_declared_total = 130/234 = 55.6%`
  （flexray 104 计入分母但不计通过——发布版缺头，上游 CI 输入亦声明 "Available is 'can'"）
- **当前配置可执行集合口径**：`130/130 = 100%`
- 恢复条件：上游发布含 flexray 头的版本（≥ v1.1.0-beta.2）后，以 `MODULE_LIST=all` 重建即可全量执行

## 二、鸿蒙专项测试（独立于上游测试，新增并实际运行）

- 源文件：`fmi_3_ls_bus_ohos_test.cpp`（本次适配新增，非上游复述）
- 内容：核验 fmi3UInt8/16/32/64 与 fmi3LsBusBoolean 类型尺寸 + CAN Transmit 操作字节流往返
  （构造 → 序列化 → 读取 → 断言 opCode/id/dataLength/payload）+ CAN FD Transmit + Wakeup
- 命令：`clang++ -std=c++17 -O2 -I headers -I fmi-standard/headers -o fmi_3_ls_bus_ohos_test fmi_3_ls_bus_ohos_test.cpp`
- 结果：**编译 exit 0；运行 exit 0，7/7 checks PASSED**

## 三、消费者用例（test_package，独立于上游与鸿蒙测试）

- 源文件：`test_package/test.c`——仅经已安装公开头 `#include <fmi3LsBus.h>` 调用公开 API
  （`FMI3_LS_BUS_CAN_CREATE_OP_CAN_TRANSMIT` / `BUFFER_WRITE` / `READ_NEXT_OPERATION` 等）
- 命令（conan create 内自动执行）：`cmake --build ... --target test && ./test_fmi-ls-bus`
- 结果：**1/1 ctest Passed；消费者二进制 exit 0，8/8 断言 PASSED**

## 四、门禁结论
- conan-verify：G1-G4 + L2/L4/L5 全 PASS（reports/conan-verify-report.md）
- W3 本地 CI 模拟：L0/L0j/L0k/L0m/KC/JC 全 PASS（reports/w3-local-ci.log；JC 经基线隔离复验通过）
- 断言总数：上游 130 + 鸿蒙专项 7 + 消费者 8 = **145**
