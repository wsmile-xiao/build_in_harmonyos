# unittest-cpp 2.0.0 适配笔记

## 概述

UnitTest++（unittest-cpp）是 Gothenburg 系轻量 C++ 单元测试框架（与 vramsteg 同厂）。
本包是**测试库**：以库使用者身份发布 `libUnitTest++.a` + 头，同时其自身即上游测试套件的
宿主（268 例）。

- 上游：https://github.com/unittest-cpp/unittest-cpp（tag archive，R39 合规；
  同已合入先例 archives/l/libuio/0.3.0 形态）
- 版本：2.0.0｜tarball sha256
  `74852198877dc2fdebdc4e5e9bd074018bf8ee03a13de139bfe41f4585b2f5b9`
  （本机 curl 与设备 curl(codeload) 双源同值，且与 hw-coord 登记值一致）
- 构建系统：CMake（与 autotools 双主线并存，本配方取 CMake，理由见 conandata 注释）
- 语言：C++11/14（`UnitTest++/` 45 个实源文件）｜许可：MIT｜零外部依赖
- 编译日期：2026-09-24｜状态：built｜**补丁：无（零源码修改）**

## 上游测试清点（R51 三步法 + §10.1 口径锁定）

静态宏口径（设备复核命令附后）与运行时注册口径分列，避免把跨配置宏总数当本配置分母：

| 维度 | 数 | 依据 |
|------|----|------|
| 宏注册上限（全部配置，行首锚定 grep） | 346 | `grep -cE "^[[:space:]]*(TEST|TEST_FIXTURE)[[:space:]]*\(" tests/Test*.cpp` |
| N_static（**本构建配置有效注册**，=口径分母） | **268** | 逐文件链接枚举（金标准，下表 TOTAL 列）；与 N_registered/N_executed 同源 |
| N_registered | 268 | 自定义 TestReporter 运行时枚举（`ENUM=268`），runner 输出 `Success: 268 tests passed.` 互证 |
| N_executed | 268 | 三次独立执行：①`cmake --build` POST_BUILD 自动跑；②配方 build() 显式复跑；③探索期独立运行 —— 均 268/268、0 失败 |
| 配置互斥排除 | 70 | `TestRequireMacrosWithExceptionsOff.cpp` 全文件在 `#ifdef UNITTEST_NO_EXCEPTIONS`；本配置 exceptions ON，其对版本（ExceptionsOn 35 例）全数执行通过 |
| 用例级 guard 差 | 8 | AssertHandler 8→6(-2)、MemoryOutStream 35→26(-9)、LongMacros 0→3(+3 行首锚定漏计)；均为 `_MSC_VER`/`UNITTEST_COMPILER_IS_MSVC6`/`#if defined(CHECK)` 等平台条件编译 |
| N_consumer | 1 程序 / 4 断言 | `test_package/test.cpp`（A1-A4，见下） |

per-file 链接枚举明细（static|registered）：
AssertHandler 8|6, CheckMacros 32|32, Checks 30|30, CompositeTestReporter 7|7,
CurrentTest 2|2, DeferredTestReporter 6|6, Exceptions 40|40, LongMacros 0|3,
MemoryOutStream 35|26, RequireMacrosOff 70|**0**(guard), RequireMacrosOn 35|35,
Test 7|7, TestList 4|4, TestMacros 13|13, TestResults 9|9, TestRunner 18|18,
TestSuite 1|1, TimeConstraint 4|4, TimeConstraintMacro 4|4, UnitTestPP 13|13,
XmlTestReporter 8|8 → Σ=268。

## 适配中撞到的真实问题（零补丁，全部官方开关）

| # | 症状（第一条真实错误，逐字） | 根因 | 解决方案 | 结果 |
|---|------------------------------|------|----------|------|
| 001 | `clang-15: error: -Wl,--code-sign: 'linker' input unused [-Werror,-Wunused-command-line-argument]`（每个 .cpp 编译行，make Error 1） | OHOS 工具链经全局编译参数注入 `-Wl,--code-sign`（HarmonyOS ELF 签名参数，链接期必需）；clang 在**编译**阶段视其为 unused 告警；上游 `UTPP_AMPLIFY_WARNINGS`（默认 ON）注入 `-Wall -Wextra -Werror` 把该告警升级为硬 error | 用上游自带 option `-DUTPP_AMPLIFY_WARNINGS=OFF`（其 README 明示的降级路径），不改上游源码、不动签名参数 | configure+build+测试全绿 |
| 002 | 上游 `cmake_minimum_required(VERSION 2.8.1)` 被 CMake 4.1.2 拒绝（既有经验签名） | 版本声明通道（经验汇总 §1618/E103/E187 家族，**非**新签名） | `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 经 cache_variables 注入 | 配置通过 |

## SignalTranslator 真机验证（派单核心问题 + §10 反假通过）

派单要求核实 `Posix/SignalTranslator.cpp`（`sigaction` + `sigsetjmp/siglongjmp`，
`sa_flags=0` 无 `sigaltstack`）在 OHOS/musl/hishell 下是否成立。双向证据：

1. **上游正验证**：Release（`-DNDEBUG`，flags.make 实测确认）下
   `CrashingTestsAreReportedAsFailures`（tests/TestTest.cpp:78，内部把 null 跳转为函数
   指针调用触发 SIGSEGV，断言被计为 1 失败）在 268 例枚举名单中（`T|DefaultSuite|
   CrashingTestsAreReportedAsFailures`）且真实通过。
2. **消费者反向验证**（test.cpp A2）：链接**已发布库产物**运行故意崩溃测试——
   `*nullptr=42` → 进程未死，`TestResults.GetFailureCount()==1`（SIGSEGV 被翻译为
   "Unhandled exception: test crashed" 失败记录）。若翻译失效，探针会 SIGSEGV
   直接死亡（rc=139），不可能打印 PASS —— 该断言形态在结构上排除假通过。

结论：**信号翻译机制在 OHOS/musl 下成立**（本包产品行为，记入 manifest compatibility；
非本草稿主题）。

## 配方要点

- `package_type="static-library"`：上游 CMake 写死 `add_library(UnitTest++ STATIC)`，
  不虚假声明 shared 选项。
- `UTPP_INCLUDE_TESTS_IN_BUILD=ON`（保持上游默认）：POST_BUILD 挂钩 = 上游测试在
  `conan create` 构建期真实执行（§10 硬规则）；POST_BUILD 非零退出即构建失败，
  未用 `ignore_errors`。runner `main()` 返回失败计数 → 任何用例失败都会红。
- 产物安装：`lib/libUnitTest++.a`、`include/UnitTest++/*.h`（含 Posix/ 子目录）、
  `lib/cmake/UnitTest++/`（上游自带 Config+Exports）、`lib/pkgconfig/UnitTest++.pc`、
  man 无；license LICENSE→licenses/。
- CMake 目标名含 `++`：cpp_info.libs=["UnitTest++"]；CMakeDeps 侧
  `cmake_file_name=unittest-cpp`/`cmake_target_name=unittest-cpp::unittest-cpp`。
- 探索期源码树产物锚点：runner 二进制在构建目录根部（上游未设 RUNTIME_OUTPUT），
  配方 build() 的显式复跑对 `cpp.build.bindirs` 与根部双路径兜底。

## 验证结果

```text
conan create（unittest-cpp/2.0.0）：构建通过，上游套件真实执行
  "Success: 268 tests passed." ×2（POST_BUILD + build() 复跑，见 reports/）
消费者测试 test_package（ctest consumer_assertions）：
  PASS: A1 RunAllTests==0 / A2 crash translated to exactly 1 failure /
  PASS: A3 MemoryOutStream format / A4 TestResults failure semantics
  SUMMARY: ALL PASS (0 assertion failures)
conan-verify：G0-G4 + L2/L4/L5 —— 见 reports/conan-verify-report.md
finish/W3 本地 CI 模拟：见 .ci-result.json 与 reports/w3-local-ci.log（绑定当前 HEAD）
产物：lib/libUnitTest++.a(241746B 探索期实测) + 45 头 + cmake package files + .pc
```

## 申报口径（供 PR 两表与 §12.72 复算，单一真相源）

- 上游表合计 = **268**（本构建配置有效注册；宏上限 346 的差额逐项说明在上表，
  两口径都在 notes 留痕，宁高勿低不适用——分母按注册口径完整未缩）；
- 适配后合计 = 268（全部执行通过）+ 消费者 4 断言（1 程序）= **272 ≥ 268** ✓；
- 通过率：执行 268/268（100%）；消费者 4/4（100%）。

## 注意事项

- 本包是测试框架：下游消费者（其他包）用 `find_package(unittest-cpp)`/链接
  `unittest-cpp::unittest-cpp`；崩溃翻译依赖 posix 信号语义，OHOS 实测成立，
  但在无信号投递的环境（如某些沙箱）会退化为进程死亡 —— 属上游设计。
- `UNITTEST_TIME_CONSTRAINT` 类用例在 CI 高负载下有计时敏感性，上游默认阈值宽松，
  本次三次执行未现抖动。

## 最终状态

- unittest-cpp/2.0.0：built（conan create 通过、上游 268/268、消费者 4/4、
  门禁全绿后由 finish 收口）；分支 feat/unittest-cpp-2.0.0；PR 与 CI 状态以
  登记表/平台为准。
---

**编译结束**: 2026-09-24 10:13
**最终状态**: built
