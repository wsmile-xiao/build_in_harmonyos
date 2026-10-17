# CLI11

CLI11 是一个用于 C++11 及以上版本的命令行解析库，提供丰富的功能和简洁的接口。

## 功能概述

- **简单易用**：只需 `#include <CLI/CLI.hpp>` 即可使用
- **Header-only**：无需编译，直接包含头文件
- **丰富的选项类型**：支持字符串、整数、浮点数、布尔值、向量等
- **子命令**：支持嵌套子命令
- **配置文件**：支持从 INI 配置文件读取
- **验证器**：内置多种验证器，支持自定义验证
- **多平台**：支持 Linux、macOS、Windows、OHOS

## OHOS 适配

### 特性
- **Header-only 库**：无需编译二进制，只需安装头文件
- **CMake INTERFACE library**：通过 CMake 安装头文件和配置文件
- **无外部依赖**：纯头文件库，不需要任何依赖

### 已知问题
- 无已知问题

### 与 Linux 的差异
- 需设置 `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=str(self.settings.arch)` 规避 E092（CMake 不识别 OHOS 平台）

## 依赖关系

### 编译依赖
- 无

### 可选依赖
- 无

## 使用方式

```cmake
# CMakeLists.txt
find_package(CLI11 REQUIRED)
target_link_libraries(my_app PRIVATE CLI11::CLI11)
```

```cpp
#include <CLI/CLI.hpp>
#include <iostream>

int main(int argc, char** argv) {
    CLI::App app{"My program"};

    std::string filename;
    app.add_option("-f,--file", filename, "Input file");

    CLI11_PARSE(app, argc, argv);

    std::cout << "File: " << filename << std::endl;
    return 0;
}
```

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| [2.6.2](./2.6.2/) | built | 2026-08-07 |

## 参考资料

- GitHub: https://github.com/CLIUtils/CLI11
- 文档: https://cliutils.github.io/CLI11/book/
