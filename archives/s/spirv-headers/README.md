# spirv-headers

SPIR-V Headers - SPIR-V 规范的机器可读文件。

## 描述

SPIR-V（标准便携式中间表示）是着色器的二进制中间表示。SPIR-V Headers 仓库包含 SPIR-V 规范的机器可读文件，包括：

- 所有 SPIR-V 版本的头文件（1.0、1.1、1.2、unified1）
- 用于解析 SPIR-V 指令的 JSON 语法文件
- C/C++ 头文件（spirv.h、spirv.hpp、spirv.hpp11）
- 其他语言绑定（spirv.cs、spirv.lua、spirv.py、spirv.json）

## 分类

图形 / Vulkan SDK

## 依赖

无（纯头文件库）

## 可用版本

- vulkan-sdk-1.3.290.0

## 安装

这是一个纯头文件库。安装后：
- 头文件：`$PREFIX/include/spirv/`
- CMake 配置：`$PREFIX/share/cmake/SPIRV-Headers/`
- pkg-config：`$PREFIX/share/pkgconfig/SPIRV-Headers.pc`

## 使用方法

```cmake
find_package(SPIRV-Headers REQUIRED)
target_link_libraries(your_target SPIRV-Headers::SPIRV-Headers)
```

或使用 pkg-config：
```bash
pkg-config --cflags SPIRV-Headers
```

## 源码

https://github.com/KhronosGroup/SPIRV-Headers