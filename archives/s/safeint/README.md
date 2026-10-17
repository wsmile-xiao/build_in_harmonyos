# safeint

SafeInt 是一个 MIT 许可的 C/C++ 仅头文件整数安全运算库，用于检测整数转换和算术运算中的溢出、下溢及除零错误。

## HarmonyOS 适配

- 使用官方 `3.0.28a` 标签源码，打包 `SafeInt.hpp`、`safe_math.h` 和 `safe_math_impl.h`。
- 构建并执行上游 Clang 测试矩阵，包括默认、禁用 intrinsics、禁用 int128 和 C safe_math 测试。
- Conan 消费者测试覆盖 C++ SafeInt API、C safe_math API，以及 HarmonyOS aarch64/Clang 平台特性。

## 参考

- 上游仓库：https://github.com/dcleblanc/SafeInt
- 许可证：MIT
