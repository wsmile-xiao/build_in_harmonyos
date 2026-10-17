# unity 2.7.0 适配笔记

## 编译环境
- 构建系统: makefile（test/Makefile 自检 + src/unity.c 手动编译共享库）
- 编译日期: 2026-09-02
- 编译器: clang（-std=c99 -O2，OHOS 真机 armv8）
- 状态: built

## 编译步骤

Unity 核心是单文件 C 库（src/unity.c + src/unity.h + src/unity_internals.h），
无 configure 脚本，采用模式 B：上游自检 + 手动编译共享库。

1. 下载源码（GitHub v2.7.0 tag tarball，sha256 已核验）
2. `make -C test CC=clang CFLAGS='-O2' test` — 上游官方自检套件，
   8 个自检可执行文件（runner 由上游自带 awk 脚本生成，无 ruby 依赖）
3. `clang -std=c99 -O2 -fPIC -shared src/unity.c
   -D UNITY_SUPPORT_64 -D UNITY_INCLUDE_DOUBLE -o libunity.so` — 被测库本体
4. 手动安装到包目录（include/unity.h、include/unity_internals.h、lib/libunity.so、
   extras 头文件、LICENSE.txt）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `UNITY_OUTPUT_CHAR` 经 CMake `-D` 传入触发 "function-style preprocessor definitions may not be passed on the compiler command line" 告警 | CMake 无法可靠传函数式宏 | 改为测试源码 `#include <unity.h>` 前 `#define` |
| 2 | `extern void UNITY_OUTPUT_CHAR_HEADER_DECLARATION;` 展开报 "expected identifier or '('"（定义值带引号时）→ "conflicting types for 'putcharSpy'"（手写 `int putcharSpy(int);` 前向声明与 `extern void` 冲突） | 上游头按 `extern void <MACRO>;` 生成声明，MACRO 须展开为无返回类型声明 | 宏值定义 `putcharSpy(int)`（不带引号、不带 int 返回类型），spy 函数签名 `void f(int)`，删除手写前向声明 |
| 3 | double 断言运行时报 "Unity Double Precision Disabled" | `UNITY_INCLUDE_DOUBLE` 是双侧编译期开关，仅库侧开启不够 | 库侧 conanfile build() 开启 + 消费者侧 CMake `target_compile_definitions` 同时开启（与上游 test/Makefile doubles 套件同款） |
| 4 | 链接失败：`setUp`/`tearDown` undefined | Unity 约定每个测试程序必须提供这两个函数 | 测试源码提供空实现 |
| 5 | `TEST_ASSERT_EQUAL_MEMORY` 失败（Byte 1 Expected 0x02 Was 0x00） | 期望侧用 `int buf[4]` 与字面量比较，int 小端补零字节 + -O2 相邻字面量合并进 rodata 的填充字节污染 memcmp | 比较两侧都用 `unsigned char[4]` 字节数组 |

## 源码修改

无源码修改。Unity 2.7.0 在鸿蒙平台使用 clang 编译无需任何代码改动。

## 依赖版本

无外部依赖。Unity 是 100% ANSI C99 单文件库，仅依赖标准 C 库。

## 验证结果

- 上游官方测试（`make test`）: **869/872 通过，0 失败，3 ignored**（ignored 为
  floats 套件内上游设计的条件性跳过，非适配问题）
  - arrays 274/274、core 26/26、doubles 101/101、float 99/102（3 ignored）、
    integers 258/258、integers_64 55/55、memory 14/14、strings 42/42
  - 3 ignored 定位：`test/tests/test_unity_floats.c:1211` 的
    `#if defined(UNITY_EXCLUDE_FLOAT_PRINT) || defined(UNITY_INCLUDE_DOUBLE) ||
    !defined(USING_OUTPUT_SPY)` 守卫触发 `TEST_IGNORE()`；上游 `test/Makefile`
    的 DEFINES 自带 `-D UNITY_INCLUDE_DOUBLE`，float 打印 spy 被 double 路径
    接管，`testFloatPrinting` / `testFloatPrintingRoundTiesToEven` /
    `testFloatPrintingRandomSamples` 按上游设计跳过（本机 OHOS aarch64
    clang-15 实跑复现，0 Failures）
- conan create（ohos-aarch64 profile）: 编译/打包/测试全链路 EXIT=0
- 冒烟测试（test_unity.c）: 2/2 通过
- 鸿蒙特有测试（test_unity_ohos.c）: 4/4 通过
