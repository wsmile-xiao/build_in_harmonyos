# DRAFT-easyhttpcpp-2.1.0-ohos-libcxx-long-long-limits-macros：OHOS libc++ 缺失 LONG_LONG_MIN/MAX 宏

## 现象

在 OHOS aarch64（libc++，clang 15.0.4）下编译 easyhttpcpp 2.1.0 上游单元测试
`tests/unittests/db/ContentValuesUnitTest.cpp` 时，编译器报未声明标识符：

```text
error: use of undeclared identifier 'LONG_LONG_MIN'
error: use of undeclared identifier 'LONG_LONG_MAX'
error: use of undeclared identifier 'ULONG_LONG_MAX'
```

## 根因

上游测试代码使用了 `LONG_LONG_MIN` / `LONG_LONG_MAX` / `ULONG_LONG_MAX`
宏（原代码仅对 Windows 分支做了定义，UNIX/Linux 分支依赖 libc 隐式提供）。
OHOS libc++（musl 系）与 glibc 不同，不在全局命名空间默认导出这组
`LONG_LONG_*` 传统宏，导致测试编译失败。C 标准规定的名称是
`LLONG_MIN` / `LLONG_MAX` / `ULLONG_MAX`（来自 `<climits>`）。

## 可复用修复模式

对使用 `LONG_LONG_MIN`/`LONG_LONG_MAX`/`ULONG_LONG_MAX` 的上游代码，增加
非 Windows 分支的定义，从标准宏映射：

```cpp
#include <climits>
#if defined(_WIN64)
#define ULONG_LONG_MAX _UI64_MAX
#define LONG_LONG_MIN _I64_MIN
#define LONG_LONG_MAX _I64_MAX
#elif defined(_WIN32)
#define ULONG_LONG_MAX ULONG_MAX
#define LONG_LONG_MIN LONG_MIN
#define LONG_LONG_MAX LONG_MAX
#else
#define ULONG_LONG_MAX ULLONG_MAX
#define LONG_LONG_MIN LLONG_MIN
#define LONG_LONG_MAX LLONG_MAX
#endif
```

适用范围：所有依赖 `LONG_LONG_MIN/MAX` 传统宏的 C/C++ 测试或源码在
OHOS/musl 系 libc++ 环境下编译失败的场景；统一改为从 `<climits>` 标准宏派生，
不改变测试语义与取值。

## 验证证据

easyhttpcpp 2.1.0 采用该修复后，`easyhttp-UnitTestRunner` 在 OHOS aarch64
（clang 15.0.4）下实际运行：1515 tests from 147 test suites，PASSED 1506 /
FAILED 9（9 项失败均为 HMDFS 无写权限断言与 URL 解码差异等平台限制，与
本修复无关）。补丁：`patches/0009-tests-unittests-db-ContentValuesUnitTest.cpp.patch`。
