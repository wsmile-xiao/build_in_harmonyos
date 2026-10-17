# rang

A Minimal, Header only Modern C++ library for colors in your terminal.

- 上游仓库: https://github.com/agauniyal/rang
- 版本: 3.3
- 许可证: Unlicense (public domain)
- 类型: header-only（单头文件 `include/rang.hpp`）
- 构建系统: cmake（INTERFACE 库，导出 `rang::rang` 目标）

## 用途

在终端中输出 ANSI 转义序列（前景色/背景色/样式），提供 `control::Off/Auto/Force`
三种控制模式与 `winTerm` 模式，支持 C++11+。

## 在 OpenHarmony / HarmonyOS PC 上

- 平台检测：OHOS 工具链预定义 `__unix__/__linux__`，rang.hpp 内部走 OS_LINUX 分支
  （该内部宏在头文件末尾被 `#undef`，属设计行为，消费方不应依赖）。
- test_package 编译时需显式追加 `-stdlib=libc++`（OHOS clang 15 仅提供 libc++；
  conan CMakeToolchain 在 OHOS 下会错误生成 `-stdlib=libstdc++`），并将
  `CMAKE_SYSTEM_NAME` 映射为 Linux。

## 使用

```cmake
find_package(rang REQUIRED)
target_link_libraries(app PRIVATE rang::rang)
```

```cpp
#include <rang.hpp>
std::cout << rang::fg::red << "red" << rang::style::reset << std::endl;
```
