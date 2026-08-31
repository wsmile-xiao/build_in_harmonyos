# minilzo

minilzo 是 LZO 项目提供的轻量级、自包含 C 语言压缩库实现，面向 LZO1X 压缩与解压场景。

## 功能概述

- 提供 `lzo1x_1_compress` 压缩 API。
- 提供 `lzo1x_decompress` 和安全解压 API。
- 纯 C 实现，无外部运行时依赖。
- 适合需要小型静态压缩组件的应用。

## 鸿蒙适配

- 使用 Conan CMake 配方构建静态库 `libminilzo.a`。
- 使用 `CMAKE_SYSTEM_NAME=Linux` 绕过当前 CMake 对 OHOS platform module 的缺失。
- 将上游 `include/lzo` 配置头文件一并安装，以满足 `minilzo.h` 的内部包含关系。
- 在 HarmonyOS PC arm64 配置下完成 Conan 干净构建和消费者测试。

## 依赖关系

- 编译依赖：无，依赖 C 标准库。
- 运行依赖：无。

## 参考资料

- 官网：https://www.oberhumer.com/opensource/lzo/
- 源码：https://www.oberhumer.com/opensource/lzo/download/lzo-2.10.tar.gz
