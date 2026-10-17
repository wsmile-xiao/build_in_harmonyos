# mitama-cpp-result

Rust 风格的 C++20 `Result<T, E>` / `Option<T>` 头文件库，提供无异常的显式
成功/错误处理。

- 上游：https://github.com/LoliGothick/mitama-cpp-result
- 许可证：MIT
- 构建系统：CMake（上游 `add_library(... INTERFACE)`，header-only）
- 包类型：header-library（无 .so/.a/.bin）
- C++ 标准：C++20（concepts / consteval）
- 运行时依赖：fmt（panic 消息格式化，`#include <fmt/core.h>`、`<fmt/std.h>` 等）

本包消费本仓库已发布的 fmt/12.2.0（上游要求 `find_package(fmt 9.0.0)`，
fmt/12.2.0 含 `<fmt/std.h>` 满足要求），不内置或下载第二份 fmt。

- 鸿蒙 PC 适配版本：见各版本目录
