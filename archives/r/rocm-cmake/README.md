# rocm-cmake

ROCm CMake 构建工具集，适用于鸿蒙 PC 平台。

## 简介

`rocm-cmake` 提供了 ROCm 项目中使用的 CMake 模块和宏。本包包含编译其他 ROCm 组件所需的 CMake 脚本。

## 上游信息

- 项目主页：https://github.com/ROCm/rocm-cmake
- 适配版本：0.12.0

## 适配说明

本包为纯 CMake 工具集（`build-scripts` 类型），无需编译二进制库，仅安装 CMake 模块文件。

## 测试结果

- 上游测试用例：35/38 通过（92.1%）
- 失败用例：
  - `pass-doc-sphinxdoxygen`：需要 `rocm-docs-core`，因鸿蒙系统缺少 `libffi` 开发包而无法安装
  - `pass-simple-soversion-env` 和 `pass-simple-soversion`：鸿蒙系统不生成 `.so.1` 符号链接，与上游测试预期不符
- 核心功能：100% 可用
