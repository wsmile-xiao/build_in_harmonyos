- **三方库名称**：unittestpp（UnitTest++）
- **上游版本**：v2.0.0（2017-01-13）
- **上游仓库地址**：https://github.com/unittest-cpp/unittest-cpp
- **适配路径**：路径 A（基础适配）
- **使用知识库**：OpenHarmony 编译智能体（ohc）；CMake 4.x 兼容与 OHOS Posix 平台层为既有知识（未新增知识条目）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 277 | 来源：上游 tests/ 目录（TestUnitTest++，21 个测试源文件 + Main.cpp）。277 = 上游测试源码注册清点（与平台审查口径一致） |
| 集成测试 | 0 | 无 |
| 其他测试 | 0 | 无 |
| **合计** | **277** | |

> 计数口径说明：277 为上游 tests/ 源码注册清点（含 9 个 `UNITTEST_USE_CUSTOM_STREAMS` 专属用例；不含 2 个仅 `UNITTEST_NO_EXCEPTIONS` 模式生效的重复用例）。本适配的构建配置（默认 `std::ostringstream`、Release/NDEBUG）实际执行的用例数为 **268**（差异 9 = custom-stream 分支未启用）。

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 277 | 不变 | 上游 tests/ 原样编译执行（零修改）；OHOS aarch64 真机实测 268/268 通过（其余 9 个为上游条件编译分支，见上） |
| 集成测试 | 0 | 不变 | — |
| 鸿蒙特有测试 | 12 | 新增 | test_package 消费者用例：正向 9 个（宏 API/夹具/套件/异常/Posix Timer/时间约束）+ 反向对照 3 个（断言失败与 raise(SIGSEGV) 信号翻译必须被如实上报） |
| **合计** | **289** | **+12** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）
- [x] **否**，上游已有测试用例覆盖

> 上游自带完整 dogfood 测试套件（21 个测试源文件、277 个用例注册，覆盖断言宏/夹具/报告器/异常/时间约束/信号翻译），无需补全。
> 另外按 L1 门禁要求新增消费者视角 test_package 12 个用例（`test_unittestpp.cpp` 正向 9 个、`test_unittestpp_negative.cpp` 反向对照 3 个），仅消费打包产物（头文件 + 静态库），不修改上游测试。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：268/268（100%）
  - OHOS aarch64 真机实测（Release/Conan 构建；`Success: 268 tests passed.`，退出码 0）
  - 另有上游默认构建配置实测 267/267（100%）——差异为 1 个仅 `NDEBUG`（Release）编译的崩溃用例
  - 与上游清点 277 的差异 9 个为 `UNITTEST_USE_CUSTOM_STREAMS` 专属用例（适配使用上游默认 `std::ostringstream` 配置，该 9 个分支不参与编译；见上方口径说明）
- 新增测试用例通过率：12/12（100%）
  - 正向 9 个全过（`Success: 9 tests passed.`，rc=0）
  - 反向对照 3 个：1 个通过 + 2 个预期失败被如实上报（rc=2，输出 `FAILURE: 2 out of 3 tests failed (2 failures).`，含 `raise(SIGSEGV)` 信号翻译 `Unhandled exception: test crashed`），对照行为符合预期

## 补充说明

- **零源码补丁**：上游 v2.0.0 在 OHOS SDK clang 15（aarch64-unknown-linux-ohos）上直接编译通过；唯一构建要求是 CMake 4.x 兼容参数 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（上游 `cmake_minimum_required(VERSION 2.8.1)`，recipe 已内置）。
- **平台层**：上游 `UnitTest++/Posix/`（`gettimeofday`/`usleep` 计时 + `sigsetjmp`/`sigaction` 信号翻译）在 OHOS musl 上原生可用，`Config.h` 依据三元组自动选中 Posix 路径。
- **静态库**：上游 CMakeLists 硬编码 `add_library(... STATIC ...)`，recipe 的 `shared` 选项在 `validate()` 显式拒绝（不产生误导性配置）。
- **已知平台注意点（实测）**：① AArch64 整数除零返回 0、不产生 SIGFPE，不能用作崩溃注入；② 本设备上"执行空指针函数调用"的硬件指令中止会让进程挂起（`raise(SIGSEGV)`/空指针数据访问/`__builtin_trap` 均能被 SignalTranslator 正常翻译），因此反向对照采用 `raise(SIGSEGV)` 保证确定性。以上已记录于 `notes.md` 与版本 manifest 的 `knowledge_gained`。
- **验证证据**：`reports/conan-create.log`（上游 268/268 + `HMBS_UPSTREAM_TEST_RESULT` + test_package 执行链）、`reports/w3-local-ci.log`（L0/L1/L1e/L2/L4/L5 本地 CI 模拟通过）、`reports/test-report.md`、`reports/audit-result.json`（W4 独立审计 verdict=pass，P0/P1=0）、`.ci-result.json`（W3 exit_code=0）。
- **用例计数口径复核**：上游 tests/ 源码注册 279（含 `UNITTEST_NO_EXCEPTIONS` 模式专属的 2 个重复用例），平台审查口径 277（剔除该 2 个模式重复用例）；本适配 Release/Conan 实测执行 268（再剔除 9 个 custom-stream 条件编译用例）、上游默认构建配置实测 267（Release 额外启用 1 个 NDEBUG-only 崩溃用例）。四组数字均有实测/源码证据，不存在少报。
