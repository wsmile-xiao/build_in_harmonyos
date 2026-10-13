# psyinf-gmtl 0.7.1 适配笔记

## 编译环境
- 构建系统: cmake（上游同时提供 SCons；测试套件上游只用 SCons）
- 编译日期: 2026-10-02
- 编译器: OpenHarmony 6.0 SDK clang 15 (aarch64-unknown-linux-ohos)
- 目标: OHOS 6.0 / armv8 / libc++ / C++17
- 状态: published

## 编译步骤

GMTL 是**纯头文件**库（`gmtl/` 下 51 个 `.h`，顶层 44 个 + `Util/ Misc/ Numerics/ External/ Fit/`），
上游 CMakeLists 只做 header 安装与 `INTERFACE` 目标，没有编译产物。

本配方：

1. `source()` 取上游 0.7.1 tarball 并 `strip_root`；
2. `generate()` 生成 CMakeToolchain，并打开 `GMTL_BUILD_UPSTREAM_TESTS`；
3. `build()` 应用补丁后 configure + build，**并执行上游 CppUnit 测试套件**；
4. `package()` 把 `gmtl/*.h` 装到 `include/gmtl/`。

```bash
conan create . -pr:h=ohos-aarch64 -pr:b=default
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游测试套件无法构建：只有 `SConstruct`/`SConscript`，没有 CMake | 上游没为测试提供 CMake 构建 | 补丁 `0001` 新增 `Test/TestSuite/CMakeLists.txt`，源码清单与 `TestCases/SConscript` 的 33 个 TestCase + `runner.cpp` 完全一致；顶层 `CMakeLists.txt` 加 `GMTL_BUILD_UPSTREAM_TESTS` 开关挂载 |
| 2 | `fatal error: 'cppunit/extensions/MetricRegistry.h' file not found` | CppUnit 在 1.12.x 之后**删除了** `MetricRegistry` 与整套 `CPPUNIT_METRIC_*` 宏；已核实 1.15.1 的 include 树中完全不存在该名字。GMTL 0.7.1（2022 冻结）中 `CPPUNIT_METRIC*` 宏仍出现 596 次（涉及 29 个文件） | 补丁新增兼容头 `Test/TestSuite/compat/cppunit/extensions/MetricRegistry.h`，用 CppUnit 1.15.1 的公开 API 重建该接口（首观测建立基线、后续观测按 warn/err 相对容差比较）。这样 metric 套件（28 个套件 / 217 条用例）仍然是**真实注册、真实参与编译**的用例，而不是被静默删掉。但需注意：本配方执行的 `noninteractive` 路径**不运行**它们（runner 按 argv[1] 选择套件），那 217 条不计入任何通过率 |
| 3 | `error: redefinition of '_cppunit_metric_t0'` | 兼容头最初把时间戳放在宏里的局部变量，而 GMTL 单个测试体内会连续出现多组 START/STOP | 改成与原始 CppUnit 相同的设计：时间戳存在 registry 里（`markStart/markStop/elapsed`），不再依赖局部变量 |
| 4 | `error: no member named 'mEmpty' in 'gmtl::AABox<float>'`（AABoxTest.cpp 5 处） | 上游测试与自己的头文件脱节：`AABox::mEmpty` 早已改名为 `mInitialized`，`AABoxTest.cpp` 没跟着改 | 补丁把 5 处改为等价的 `isEmpty()` / `setEmpty(false)` |
| 5 | `error: no matching function for call to 'intersect'`（SphereTest.cpp 3 处） | 上游漂移：API 形参是 `unsigned int&`，测试里 4 处声明为 `int hits;` | 补丁把 `int hits;` 改成 `unsigned int hits;` |
| 6 | 运行时 1 例失败：`OutputTest.cpp:141` 断言 `"(1, 2, 3) (4, 5, 6) false"` | 上游漂移：`operator<<` 现在打印 `mInitialized`（该 box 为 `true`），测试仍按旧的 `mEmpty` 取反语义写成 `false` | 补丁把期望值改为 `"... true"` |
| 7 | `package(): WARN: No files in this package!`，消费端报 `non-existent path .../p/include` | `copy(dst="include/gmtl")` 的**相对 dst 是按当前工作目录解析的**，而 `package()` 期间 cwd 是 build 目录 —— 文件被复制进 build 目录，包里空无一物 | `dst` 一律用 `os.path.join(self.package_folder, ...)` 拼绝对路径 |
| 8 | 交叉编译下 test_package 的 `test()` 因 `can_run()` 为假而不执行 | OHOS 是交叉目标 | `test()` 里回退到 profile 的 `CMAKE_CROSSCOMPILING_EMULATOR`（与配方同一个 qemu 包装器）执行消费者二进制 |

## 源码修改

补丁 `patches/0001-build-upstream-tests-on-ohos.patch`（单文件，含以下 6 处改动）：

| 文件 | 改动 |
|------|------|
| `CMakeLists.txt` | 新增 `GMTL_BUILD_UPSTREAM_TESTS` 选项与 `add_subdirectory(Test/TestSuite)` |
| `Test/TestSuite/CMakeLists.txt` | 新增：上游测试套件的 CMake 移植，源码清单与上游 `SConscript` 一致 |
| `Test/TestSuite/compat/cppunit/extensions/MetricRegistry.h` | 新增：CppUnit 1.12 时代 MetricRegistry API 的兼容实现 |
| `Test/TestSuite/TestCases/AABoxTest.cpp` | `mEmpty` → `isEmpty()` / `setEmpty(false)`（5 处） |
| `Test/TestSuite/TestCases/SphereTest.cpp` | `int hits;` → `unsigned int hits;`（4 处） |
| `Test/TestSuite/TestCases/OutputTest.cpp` | AABox 流输出期望值 `false` → `true`（1 处） |

**未改动 `gmtl/` 下的任何库头文件** —— 全部改动都只为让上游测试能编译并真实执行。

## 依赖版本

- cppunit/1.15.1（`test_requires`，构建期测试框架，不进入运行时依赖）
  OHOS 预编译二进制：`cppunit/1.15.1:f23d5a9b1d537641c03c7814478a2fadb727650a`

无运行时依赖（纯头文件）。

## 验证结果

上游测试套件（qemu 执行，`noninteractive` 聚合路径）：

```bash
conan create . -pr:h=ohos-aarch64-run -pr:b=default
# RUN: "/root/ohpc/bin/ohos-qemu-aarch64" ".../Test/TestSuite/runtests" noninteractive
# OK (208)
```

消费者端到端（rule12，同一 qemu 包装器执行）：

```bash
# RUN: /bin/bash -c '"/root/ohpc/bin/ohos-qemu-aarch64" "./consumer"'
# checks: 25  failed: 0
# CONSUMER E2E: PASSED (25/25)
```

本地 harness：`conan exit=0`。

## 注意事项

- 上游 `Test/TestSuite/TestCases/ParametricCurveTest.cpp` **不在** `TestCases/SConscript` 清单里
  （其 `#include "ParametriCurveTest.h"` 少了一个 `c`：源码包里实际存在的是
  `ParametricCurveTest.h`），上游从不编译它；
  本配方的 CMake 移植严格照抄上游清单，因此同样不编译，这是**忠实复现上游行为**而非遗漏。
- metric 套件的计时断言在 qemu 下按「首次观测建立基线」处理（交叉目标上不存在历史基线），
  与 CppUnit 1.12 在全新机器上的行为一致。
