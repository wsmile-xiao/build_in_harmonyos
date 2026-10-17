# Test Report — miniscript 1.6.2

## 1. 上游测试枚举台账（source_declared_total）

官方 tag v1.6.2 源码中按可复制枚举规则发现的测试声明：

| # | 声明位置（源码注册项） | 分类 | 是否独立上游用例 | 说明 |
|---|---|---|---|---|
| 1 | `MiniScript-cpp/src/MiniScript/UnitTest.cpp` — `TestCaseItself` | 用户测试源（框架自测） | 是 | RegisterUnitTest 注册，框架自身冒烟 |
| 2 | `MiniScript-cpp/src/MiniScript/Dictionary.cpp` — `TestDictionary` | 用户测试源 | 是 | 18 断言，Dictionary 行为 |
| 3 | `MiniScript-cpp/src/MiniScript/List.cpp` — `TestList` | 用户测试源 | 是 | 24 断言，List 行为 |
| 4 | `MiniScript-cpp/src/MiniScript/MiniscriptLexer.cpp` — `TestLexer` | 用户测试源 | 是 | 17 断言，词法分析 |
| 5 | `MiniScript-cpp/src/MiniScript/MiniscriptParser.cpp` — `TestParser` | 用户测试源 | 是 | 6 断言，语法解析 |
| 6 | `MiniScript-cpp/src/MiniScript/MiniscriptTypes.cpp` — `TestValue` | 用户测试源 | 是 | 25 断言，Value 类型 |
| 7 | `MiniScript-cpp/src/MiniScript/SimpleString.cpp` — `TestString` | 用户测试源 | 是 | 76 断言，String/UTF-8 |
| 8 | `MiniScript-cpp/src/MiniScript/SimpleVector.cpp` — `TestSimpleVector` | 用户测试源 | 是 | 24 断言，SimpleVector |
| 9 | `MiniScript-cpp/src/MiniScript/SplitJoin.cpp` — `TestSplitJoin` | 用户测试源 | 是 | 9 断言，SplitJoin |
| 10 | `MiniScript-cpp/src/MiniScript/UnicodeUtil.cpp` — `TestUnicodeUtil` | 用户测试源 | 是 | 22 断言，Unicode 工具 |
| 11 | `TestSuite.txt` — `minicmd --itest` | 集成测试套件（框架官方断言脚本） | 是 | 语言级集成测试（逐行断言） |
| — | `MiniScript-cpp/demo/*.ms`（5 个示例脚本） | 样例 | 否（非独立用例，仅示例） | 不计入用例数，仅展示 |
| — | `MiniScript-cs/*`（C# 实现） | 其他语言实现 | 否（MINISCRIPT_BUILD_CSHARP=OFF 未构建） | 不在 C++ 适配范围 |
| — | 框架头/内部宏（QA.h Assert 宏等） | 框架基础设施 | 否（宏非独立用例） | 不计入 |

**source_declared_total = 11**（10 个 UnitTest 注册类 + 1 个集成测试套件）

## 2. 配置实例化映射（configured_executable_total）

| 源码声明 | 预处理/构建条件 | 构建目标 | 注册项 | 实际执行 |
|---|---|---|---|---|
| #1-#10 注册类 | 编译入 `tests-cpp`（UnitTest.cpp 带 UNIT_TEST_MAIN） | `tests-cpp` | ctest #1 `Miniscript.cpp.UnitTests` | ✅ 运行通过 |
| #11 TestSuite.txt | `minicmd --itest ${CMAKE_SOURCE_DIR}/TestSuite.txt` | `minicmd`（miniscript） | ctest #2 `Miniscript.cpp.Integration` | ✅ 运行通过 |

**configured_executable_total = 2**（tests-cpp 承载 10 个注册类，miniscript 承载集成套件）

## 3. 双口径统计

| 口径 | 值 |
|---|---|
| source_declared_total | 11 |
| configured_executable_total | 2 |
| executed_passed_total | 11（10 注册类 + 1 集成套件全过） |
| 失败数 | 0 |
| 未运行/未实例化 | 0 |
| **全量通过率** | **11/11 (100.0%)** |
| 当前配置可执行集合通过率 | 2/2 ctest (100%) |

## 4. 实际运行证据

```bash
$ ctest --output-on-failure
Test #1: Miniscript.cpp.UnitTests ......... Passed    0.02 sec
Test #2: Miniscript.cpp.Integration ....... Passed    0.14 sec
100% tests passed, 0 tests failed out of 2
```

- 命令：`cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DMINISCRIPT_BUILD_TESTING=ON -DMINISCRIPT_BUILD_CSHARP=OFF` + `cmake --build build -j4` + `ctest --output-on-failure`
- cwd：`/storage/Users/currentUser/tmp/builds/miniscript-1.6.2.work`
- 退出码：0

## 5. 平台适配说明

- OHOS/arm64 默认 `char` 为 unsigned，上游 `TestString` 断言 `s.atB(0) == -26`（期望 0xE6=230 被解释为 signed -26）在默认编译下打印 Assert 失败。适配在配方 `generate()` 注入 `-fsigned-char`（C/CXX），与 x86 Linux 的 signed char 语义对齐后全部断言通过、CLI 启动无噪音。属编译标志对齐，非修改上游测试。
- 单元测试框架 `_Error` 仅打印不计数，`UnitTest::RunAllTests()` 由 `main()` 无条件调用；CLI 启动时同样执行自测（修复前会向 stderr 打印 Assert 失败，不影响功能）。

## 6. test_package 消费者测试（鸿蒙专项）

- `test_package/test.cpp`：通过公开 `MiniScript::Interpreter` API 运行 `x = 6 * 7; print "answer is " + x`，校验输出 `answer is 42` 与全局变量 `x == 42`（GetGlobalValue）。真实调用公开头文件/API 并验证可观察结果。
- 随 conan create 执行并通过（G2 PASS）。
