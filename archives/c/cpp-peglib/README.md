# cpp-peglib

cpp-peglib 是一个基于 C++17 的单头文件 PEG（Parsing Expression Grammars）解析库。

## 功能概述

- 提供 `peglib.h` 单头文件接口。
- 支持 PEG 语法、Packrat 解析、左递归、AST、Unicode 和错误恢复。
- 通过 CMake 提供上游测试、示例和可选的 `peglint` 工具构建目标。

## OHOS 适配

- 采用顶层 CMake 的 `peglib` `INTERFACE` 目标，生产包不生成 `.a`/`.so`。
- 配方使用 C++17，安装时只复制 `peglib.h` 到 `include/`。
- 上游仓库同时包含独立的 `rust-peglib/` 子项目；本 Conan 包仅适配顶层 C++ cpp-peglib 项目，Rust 子项目不参与 CMake 构建。

## 依赖关系

- 生产包无运行时或编译时 Conan 依赖。
- 上游测试由其 CMake 测试目录通过 FetchContent 获取 GoogleTest；该测试依赖只用于源码测试，不进入生产包依赖闭包。

## 参考资料

- 上游仓库：https://github.com/yhirose/cpp-peglib
- 上游主页：https://yhirose.github.io/cpp-peglib/
