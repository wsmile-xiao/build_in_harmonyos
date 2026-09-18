# libfixmath

libfixmath 是一个面向资源受限场景的 C/C++ Q16.16 定点数数学库。本归档将上游 `0-20220222` 版本适配至 HarmonyOS PC AArch64，并通过 Conan 2 提供可复现的静态库包。

## 功能概述

- 提供 Q16.16 定点数转换、算术和饱和运算。
- 提供平方根、指数、对数、三角函数和线性插值。
- 同时提供 C API 与轻量 C++ 包装类。

## OHOS 适配

- 使用 HarmonyOS SDK Clang/Clang++ 和 CMake 构建。
- 无需修改上游源码，保持 API 与行为一致。
- 打包 C API、C++ 包装头文件与 `liblibfixmath.a`。
- 构建阶段执行上游全部 12 个 CTest 配置变体。
- 消费阶段验证 C/C++ API，并新增 HarmonyOS AArch64/musl ABI 专项测试。

已知问题：无。

与 Linux 的差异：包消费测试额外校验 HarmonyOS 的 OHOS/AArch64/musl/小端 ABI；公开库 API 无差异。

## 依赖关系

库本体没有第三方依赖。测试和上游辅助程序仅使用目标系统提供的 C/C++ 运行库与数学库。

## 使用

Conan 引用：

```text
libfixmath/0-20220222
```

CMake 消费目标：

```cmake
find_package(libfixmath CONFIG REQUIRED)
target_link_libraries(your_target PRIVATE libfixmath::libfixmath)
```

C 头文件为 `<libfixmath/fix16.h>`，C++ 包装头文件为 `<libfixmath/fix16.hpp>`。

## 参考资料

- 仓库：https://github.com/PetteriAimonen/libfixmath
- 许可证：MIT
