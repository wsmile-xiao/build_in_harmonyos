# nanobind

Tiny and efficient C++/Python bindings library (header + CMake tooling).

## 功能概述

- 轻量 C++11/17 绑定框架，API 类似 pybind11
- 提供 `nanobind_add_module` CMake 宏与 `nanobind-config.cmake`
- 供下游项目编译 Python 扩展模块

## OHOS 适配

- 构建：CMake 安装型配方，对齐 Homebrew：
  - `NB_TEST=OFF`
  - `NB_USE_SUBMODULE_DEPS=OFF`
  - `NB_CREATE_INSTALL_RULES=ON`
- **关键**：`NB_INSTALL_DATADIR` 须设为 `package_folder/nanobind` 绝对路径（CMake `CACHE PATH` 会把相对 `nanobind` 锚到 build 目录，导致空包）
- 依赖：`robin-map/1.4.1`（CMake 包名 `tsl-robin-map`，方案 A / R36）
- 验收：`test_package` 编译 `my_ext` 扩展并 `import` 调用 `add(1,2)==3`
- Python 测试对齐制品仓 **3.12.x**（不强制 Homebrew 的 3.14）
- 库类型，**不要** `commands.json`（R38）

## 依赖关系

- 编译/安装：cmake
- 库依赖：robin-map 1.4.1
- 测试：python3 + Development.Module 头文件/库

## 参考资料

- 上游：https://github.com/wjakob/nanobind
- Homebrew：https://formulae.brew.sh/formula/nanobind
- 前置依赖：Homebrew https://formulae.brew.sh/formula/robin-map
- 适配方案：`适配文件/适配文档/nanobind-适配方案.md`
