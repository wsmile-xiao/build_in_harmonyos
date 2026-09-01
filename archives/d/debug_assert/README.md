# debug_assert

Simple, flexible and modular assertion macro for C++.

- 官方仓库: https://github.com/foonathan/debug_assert
- 许可证: Zlib（详见 LICENSE）
- 形态: 单头文件 header-only（`debug_assert.hpp`），无编译期产物

## OHOS 适配

header-only 库，配方通过 Conan 打包头文件至 `include/` 与 `include/debug_assert/`
（兼容无前缀与带目录两种 `#include` 方式），不引入编译期依赖。
