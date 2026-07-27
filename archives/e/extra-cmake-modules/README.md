# extra-cmake-modules (ECM)

> Extra CMake Modules — KDE 社区扩展 CMake 模块包

## 简介

ECM 为 CMake 项目提供额外模块、find-modules、kde-modules 和 toolchain 文件，主要服务于 KDE Frameworks 6 生态（ki18n、karchive、kdoctools 等），但可用于任何 CMake 项目。

## 鸿蒙适配说明

- **构建系统**：CMake（cmake-only，无 C/C++ 编译产物）
- **平台**：OHOS / Linux / macOS / Windows
- **依赖**：零运行时依赖
- **适配版本**：6.19.0
- **上游源**：https://download.kde.org/stable/frameworks/6.19/extra-cmake-modules-6.19.0.tar.xz
- **SHA256**：a4f0c1d8181f43e9af4b9b44696c77760b5bc9dae5bdb921f090bce664e9ca84

## 下游引用

```python
# Conan 2.x
self.requires("extra-cmake-modules/6.19.0")
# CMake
find_package(ECM REQUIRED CONFIG)
```

## 已知平台限制

- ECM 自身无平台限制（纯 cmake 模块）
- 测试套需 Python3/Sphinx/ReuseTool（OHOS 开发机可能缺失，cmake configure 会 warning 但非阻塞）
