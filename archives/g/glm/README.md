# glm

## 简介

GLM (OpenGL Mathematics) 是 header-only C++ 数学库，API 设计兼容 GLSL
着色器语言，提供向量、矩阵、四元数等图形学常用数学操作。

## OHOS 适配

GLM 1.0.3 的 Conan 配方声明 `package_type = "header-library"`，保留上游
安装的头文件和 CMake 配置，导出 `glm::glm` INTERFACE target，不产生运行库
也不依赖第三方 Conan 包。OHOS profile 将目标绑定到 Linux/aarch64；独立的
官方源码构建完整执行了 189 个 CTest 用例。

旧版本 0.9.9.8 的手动安装说明仍适用于不使用 Conan 的场景：可将 `glm`
头文件安装到 `~/usr/local/include/glm`。CMake 4.1.2 不支持早期的
`cmake_minimum_required` 版本时，应使用 Conan 生成的工具链和上游安装入口。

## Conan usage

```cmake
find_package(glm CONFIG REQUIRED)
target_link_libraries(my_app PRIVATE glm::glm)
```

```cpp
#include <glm/glm.hpp>
glm::vec3 direction(1.0f, 2.0f, 3.0f);
```

## 依赖

- 编译依赖：无（header-only）
- 运行依赖：无

## 参考

- GitHub：https://github.com/g-truc/glm
- 1.0.3 release：https://github.com/g-truc/glm/releases/tag/1.0.3
