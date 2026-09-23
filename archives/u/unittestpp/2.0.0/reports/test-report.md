# unittestpp 2.0.0 测试报告

> **项目**: unittestpp（UnitTest++ 2.0.0）
> **测试日期**: 2026-09-16
> **测试环境**: HarmonyOS HongMeng Kernel 1.12.0 aarch64（OHOS SDK clang 15.0.4，CMake 4.4.3）
> **测试类型**: 上游官方测试套件（TestUnitTest++）+ Conan 消费者测试

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 上游测试用例（源码注册清点，平台口径） | 277 | — |
| 上游测试实执行（Release/Conan 构建） | 268 | 100% |
| 通过 (PASS) | 268 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |
| 消费者正向用例（test_package） | 9 | 100% |
| 消费者反向对照用例（预期失败） | 3（2 失败被如实上报） | — |

**核心功能通过率**: ✅ **100%**（268/268 实执行；清点 277 中 9 个为上游
`UNITTEST_USE_CUSTOM_STREAMS` 条件编译分支，默认 `std::ostringstream` 配置不参与编译）

---

## 二、测试结论

### 2.1 总体评价

✅ **通过**。上游 v2.0.0 在 OHOS aarch64 + clang 15 上零源码补丁编译，
上游测试 Release 构建实测 268/268 全过（另有默认构建配置 267/267；
源码清点 277，差异 9 个为 custom-stream 条件编译分支，见 3.3）；
消费者视角用例（正向 9 + 反向对照 3）验证了
断言/夹具/套件/异常/计时/时间约束与 Posix 信号翻译路径。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 无（适配未发现问题） | — | — |

### 2.3 可用功能清单

```
✅ 断言宏: CHECK / CHECK_EQUAL / CHECK_CLOSE / CHECK_ARRAY_EQUAL / CHECK_ARRAY_CLOSE / CHECK_THROW / REQUIRE
✅ 测试组织: TEST / TEST_FIXTURE / SUITE / 自定义 TestReporter
✅ 计时与约束: UnitTest::Timer / TimeHelpers::SleepMs / UNITTEST_TIME_CONSTRAINT
✅ Posix 信号翻译: raise(SIGSEGV) 等信号被翻译为测试失败而非进程崩溃
✅ 报告器: TestReporterStdout / XmlTestReporter / DeferredTestReporter
✅ 安装树: include/UnitTest++/、lib/libUnitTest++.a、lib/cmake/UnitTest++/、pkgconfig
```

### 2.4 已知限制

1. 上游构建系统只产出静态库（`add_library(UnitTest++ STATIC ...)`），
   recipe 的 `shared` 选项显式拒绝（validate）。
2. 本设备实测：测试内「执行空指针函数调用」的硬件指令中止会让进程挂起；
   `raise(SIGSEGV)` / 空指针数据访问 / `__builtin_trap` 均可正常翻译
   （反向对照采用 `raise(SIGSEGV)` 保证确定性）。
3. AArch64 整数除零返回 0 不产生 SIGFPE，不能作为崩溃注入手段。

---

## 三、测试详情

### 3.1 通过的测试

| 测试项 | 功能 | 结果 |
|--------|------|------|
| 上游 TestUnitTest++（清点 277 / Release 实执行 268） | 框架自身 dogfood 套件（断言/夹具/报告器/异常/时间约束/信号） | ✅ PASS 268/268 |
| test_unittestpp（9 用例） | 消费者宏 API/夹具/套件/异常/Posix Timer/时间约束 | ✅ PASS 9/9 |
| conan test_package 破坏性反向验证 | 移走 lib/include 后测试必须失败（CI L1e） | ✅ PASS（本地 CI gate 验证） |

### 3.2 失败（预期）的测试

| 测试项 | 原因 | 说明 |
|--------|------|------|
| check_failure_probe | `CHECK_EQUAL(42, 41)` 失败（设计如此） | 反向对照：断言失败必须被如实上报 |
| signal_probe | `raise(SIGSEGV)` 信号翻译（设计如此） | 反向对照：崩溃信号必须被翻译为测试失败 |

### 3.3 条件编译未执行的上游用例（计数口径）

| 用例/文件 | 未执行原因 |
|-----------|------------|
| TestRequireMacrosWithExceptionsOff.cpp（70 用例） | 上游条件编译（`UNITTEST_NO_EXCEPTIONS` 模式专属），默认构建与 Release 构建均不编译 |
| TestAssertHandler.cpp 内 2 个 no-exceptions 模式用例 | 仅存在于 `#else`（`UNITTEST_NO_EXCEPTIONS`）分支，默认模式不编译；平台清点 277 已剔除这 2 个 |
| TestMemoryOutStream.cpp 9 个容量/缓冲用例 | 仅在 `UNITTEST_USE_CUSTOM_STREAMS`（未定义 `UNITTEST_MEMORYOUTSTREAM_IS_STD_OSTRINGSTREAM`）配置编译；上游默认配置使用 `std::ostringstream` |
| TestTest.cpp `CrashingTestsAreReportedAsFailures` | 仅 `NDEBUG`（Release）编译：Release 实测包含（268）；上游默认配置为 267 |

---

## 四、关键问题分析

### 问题1: CMake 4.x 与上游 `cmake_minimum_required(VERSION 2.8.1)` 不兼容

**现象**：
```
CMake Error at CMakeLists.txt:1 (cmake_minimum_required):
  Compatibility with CMake < 3.5 has been removed from CMake.
```

**根因分析**：
CMake 4.x 移除了对 <3.5 的最低版本兼容；上游 CMakeLists 声明 2.8.1。

**解决方案**：
`cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})`
（CMake 官方兼容开关，须在 cmake 命令行传参），零补丁。

### 问题2: 空指针函数调用会让测试进程挂起（本设备平台行为）

**现象**：
```
（10s 无输出，进程 State:S、0 CPU，timeout 124；raise(SIGSEGV)/空指针数据写/__builtin_trap 均正常）
```

**根因分析**：
本设备上 PC=0 指令中止疑似进入平台崩溃处理通道，未回到 SignalTranslator 的
siglongjmp（对照实验：自定义最小 handler 可捕获，`raise(SIGSEGV)` 在框架内正常）。

**解决方案**：
消费者反向对照改用 `raise(SIGSEGV)`（确定性且可移植）；平台行为记录进
manifest knowledge_gained 与 notes.md。

---

## 五、测试环境

```
软件版本: unittestpp 2.0.0（上游 unittest-cpp v2.0.0, 2017-01-13, MIT）
编译配置: Conan 2.29.1 (OHOS 适配版), profile ohos-aarch64-device
          os=OHOS 6.0 / arch=armv8 / clang 15 / libc++ / cppstd=17 / Release
          CMake 4.4.3, GNU Make 4.4.1
源码: https://github.com/unittest-cpp/unittest-cpp/archive/refs/tags/v2.0.0.tar.gz
      sha256 74852198877dc2fdebdc4e5e9bd074018bf8ee03a13de139bfe41f4585b2f5b9
证据: reports/conan-create.log（268/268 + HMBS_UPSTREAM_TEST_RESULT + test_package 执行链）
      test_package/build/clang-15-armv8-17-release/{positive,negative}-run.log
```

---

*报告生成时间: 2026-09-16*
