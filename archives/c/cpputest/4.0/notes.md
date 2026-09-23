# cpputest 4.0 适配笔记

## 编译环境
- 构建系统: cmake（纯 CMake 项目）
- 编译日期: 2026-09-21
- 编译器: clang/clang++ 15（OHOS aarch64，Conan profile ci/conan/profiles/ohos-aarch64）
- 状态: built

## 编译步骤
- `cmake.configure()` + `cmake.build()` + `cmake.test()`；变量：TESTS=ON（构建上游 dogfood 套件并逐用例注册 ctest）、CPPUTEST_FLAGS=OFF（只用 Conan 注入的编译参数，R33）、WERROR=OFF、COVERAGE/MAP_FILE=OFF
- 打包：`cmake.install()`（include/CppUTest* + lib/libCppUTest.a、libCppUTestExt.a）

## 上游测试（§10.1 五维账本）
- N_static = 1363（原子用例静态全量口径，按注册宏逐项统计、不混算）：`^TEST(` 1347 ＋ `^TEST_ORDERED(` 12 ＋ `^TEST_ORDERED_C_WRAPPER(` 3（宏展开即 TEST_ORDERED，OrderedTest.h:81）＋ `^TEST_C_WRAPPER(` 1（宏展开即 TEST，TestHarness_c.h:176）；两个 C wrapper 宏各自注册原子用例，不能漏计
- 条件未编译（单列不删项，不从分母删除但也不冒充已执行）：tests/CppUTestExt/GTest2ConvertorTest.cpp 含 2 个 `TEST_F(` 用例，依赖上游 GTest 集成（CMake 选项默认 OFF，本配方未开启）→ 未注册、未执行，属"上游条件构建"类
- N_registered = 1353（二进制实际注册：CppUTestTests 835 ＋ CppUTestExtTests 518）；构建期发现脚本按**测试组**注册 78 条 ctest 条目（`binary.Group` 形态、`ctest -N` 实测 78，`-sg` 整组执行）。静态宏 1420（可执行 1363＋ignored 57）与二进制注册 1353 的差额 67 = 上游条件编译块（`CPPUTEST_USE_STD_CPP_LIB`/`CPPUTEST_SANITIZE_ADDRESS` 等开关下未纳入本构建的用例宏 66）＋ 1 个 ignored 宏位于条件块内未注册
- N_executed = 1297 原子用例（CppUTestTests 781 ＋ CppUTestExtTests 516）：**1296 通过 ＋ 1 失败**（失败项见下节申报口径）；原始输出留存 reports/upstream-fullrun-atomic.log
- N_executed（ctest 条目口径）= 78/78 全过——**如实说明**：上游 `tests/CppUTest/AllTests.cpp` 的 main 有意丢弃 `RunAllTests` 返回值（注释 "cover alternate method"），CppUTestTests 二进制恒以 0 退出，ctest 条目级结果不反映原子级失败；本包按原子口径申报，不以条目口径掩盖
- 未执行 = 56 IGNORE（二进制内：54＋2，含本包补丁转忽略的 1 个）＋ 2 GTest 条件未编译；上游 ignored 宏静态口径 57（56 `^IGNORE_TEST(` ＋ 1 `IGNORE_TEST_C_WRAPPER(`）
- N_consumer = 1：test_package/consumer_test.cpp（3 用例 8 断言 + CommandLineTestRunner 退出码判定，实测 `OK (3 tests, 3 ran, 8 checks, 0 ignored)`）

## 上游测试未全通过时的申报口径
- **失败 1 项（平台 PRNG 差异，如实申报不掩盖）**：`UtestShellPointerArrayTest/firstTestisNotTheFirstTestWithSeed1234`（UtestTest.cpp:463）——用例构造 3 元素列表后 `shuffle(1234)`（内部 `srand(1234)`＋`rand()` 生成置换，Utest.cpp:801-815），断言洗牌后首元素 ≠ 原 first。glibc 的 rand() 序列使断言成立，**musl 的 rand() 实现序列不同，srand(1234) 后的置换恰好保留 test0 在首位** → CHECK 失败（实测错误行：`UtestTest.cpp:463: error: Failure in TEST(...)`）。这是上游用例对 libc PRNG 具体序列的强绑定，属 OHOS musl 平台差异，非 CppUTest 功能缺陷，也无法在 OHOS 上修正（改断言=为通过而改测试）。按平台边界申报：N_executed 1297 中 1 项未通过，其余 1296 全过。
- **上游 main 丢弃退出码的口径说明**：`tests/CppUTest/AllTests.cpp` main 有意不返回测试结果（"cover alternate method"，上游为覆盖率设计），故 ctest 78/78 条目通过 ≠ 原子级全过；本包以二进制原始输出（`OK/Errors (N tests, M ran...)` 汇总行）为准申报原子口径，两套口径均列示。
- IGNORE_TEST 56 个（二进制内）：上游源码显式标注忽略（未完成/预期失败用例），属上游既有设计，非本次适配导致
- IGNORE_TEST +1（patches/0001-utestshell-crash-separate-process-ohos-ignore.patch，DS-11 09-21）：`UtestShell/TestDefaultCrashMethodInSeparateProcessTest` 在 OHOS 上真实 fork 子进程并解引用空指针后，**子进程不死于信号**——平台故障报告链（faultloggerd）接管后子进程陷入 R 状态自旋（实测 /proc/<pid>/status State=R、6 秒吃满 6 秒 CPU、无退出），父进程 `waitpid(WUNTRACED)` 永等，整个 ctest 条目撞 1500s 超时（DS-7 首轮 conan-verify 实测 `***Timeout 1500.06 sec`，其余 77/78 组全过）。处置遵循上游自身的 `#ifndef CPPUTEST_HAVE_FORK → IGNORE_TEST` 同型惯例（"fork 语义不可用的平台忽略此用例"），改为 OHOS 平台忽略，未删除用例本体（补丁 diff 全文保留原断言）。对照组：同组 `RunInSeparateProcessTest`（桩实现，无真实 crash）正常通过，证明 hang 仅由"故意崩溃 + 信号终止"路径触发。补丁后该组 0.055s 完成，全量 ctest 78/78 组全过。

## 依赖版本
- 无编译依赖（纯标准库 C++）

## 为什么要做这个包（下游驱动）
- weechat/4.9.4（任务 11862）上游单元测试体系基于 CppUTest；cpputest 未适配则 weechat 上游测试整体无法执行（§10 硬规则：整体 0 执行不可交付）。本包为 weechat 的拓扑前置依赖。

## 路径 B 判断
- B判定=create（DRAFT-cpputest-4.0-cmake4-policy-flag，DS-7 建草稿、DS-11 复核维持 create）：CMake>=4 删除 <3.5 policy 兼容后，`CMAKE_POLICY_VERSION_MINIMUM` **必须经命令行 cache 变量传入**（`cmake.configure(variables=...)` 即 `-D` 初始 cache，先于 CMakeLists 执行）；写进 toolchain 文件的 tc.variables 因加载时机晚于 `cmake_minimum_required` 完全无效——E103/E187 只记录了"加 flag"的结论，未记录传参通道差异，本条补全"怎么传才生效"（本包实测 tc.variables 无效反例）。

## 验证结果
- conan-verify：G0-G4（reports/conan-verify-report.md）
- 上游测试与消费者测试结果：见 reports/ 与 test_package/MANIFEST.yml

---
**编译结束**: 2026-09-21
**最终状态**: built
---

**编译结束**: 2026-09-21 15:21
**最终状态**: built
