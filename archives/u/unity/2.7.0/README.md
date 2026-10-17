# unity 2.7.0 — HarmonyOS PC 适配

Unity 是 ThrowTheSwitch 出品的 C 语言单元测试框架，100% ANSI C99、单文件核心
（`src/unity.c` + `src/unity.h` + `src/unity_internals.h`）、零第三方依赖，
用于在嵌入式/鸿蒙等目标平台上为 C 代码编写和运行单元测试。

## 包信息

| 项 | 值 |
|----|----|
| 包名 | unity/2.7.0 |
| 上游 | https://github.com/ThrowTheSwitch/Unity (tag v2.7.0) |
| 源码 sha256 | e84eb301ca7967831e68b1728f911e87fa2d345d8ddb64f897bc2f2ee24a321c |
| 许可证 | MIT |
| 构建系统 | makefile（上游自检）+ clang 手动编译共享库 |
| 适配路径 | 路径 A（基础适配）—— 零源码修改 |

## 适配说明

Unity 纯 ANSI C99、无 POSIX 系统调用，在 OHOS (armv8) 上使用 clang 原生编译
**无需任何源码修改**。

- **上游官方测试（L1，真实执行）**：配方 `build()` 中跑
  `make -C test CC=clang CFLAGS='-O2' test`，上游 8 个自检套件
  **872 用例：869 通过、0 失败、3 ignored**（integers_64 套件内上游设计的
  条件性跳过）。
- **被测库本体**：`src/unity.c` 编译为 `libunity.so`
  （`-D UNITY_SUPPORT_64 -D UNITY_INCLUDE_DOUBLE`，与上游 doubles 套件同款）。
- **鸿蒙特有测试**（`test_package/test_unity_ohos.c`，4 用例，全过）：
  版本头身份（2.7.0）/ 核心断言（int、int64、string、pointer、memory）/
  double 断言（armv8 64 位浮点路径）/ `UNITY_OUTPUT_CHAR` 输出钩子。

## 使用方式

```c
#include <unity.h>

void setUp(void) {}
void tearDown(void) {}

static void testExample(void)
{
    TEST_ASSERT_EQUAL_INT(42, 42);
}

int main(void)
{
    UnityBegin(__FILE__);
    RUN_TEST(testExample);
    return UNITY_END();
}
```

消费方链接 `unity::unity`（libunity.so）。需要 double 断言时消费者侧
同时定义 `UNITY_INCLUDE_DOUBLE`；需要自定义输出字符钩子时在
`#include <unity.h>` 前定义 `UNITY_OUTPUT_CHAR`（函数式宏，勿走命令行 -D）。

## 已知限制

- 上游 `extras/`（fixture 等）头文件随包附带但未编译为库，按需自行使用。
- `UNITY_OUTPUT_CHAR` 默认回退 `putchar`，测试二进制运行需 stdout 可用。
