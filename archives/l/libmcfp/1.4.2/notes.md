# libmcfp 1.4.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-10
- 编译器: clang/clang++
- 状态: published

## 编译步骤

libmcfp 是 header-only INTERFACE 库（CMake: `add_library(mcfp INTERFACE)`）。

1. CMake 配置:
   ```bash
   cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF
   ```
2. CMake 构建:
   ```bash
   cmake --build build
   ```
3. CMake 安装（头文件安装）:
   ```bash
   cmake --install build --prefix $HOME/tmp/mcfp-test-install
   ```
4. 验证: 编写简单 C++ 程序 include mcfp/mcfp.hpp 并使用 API，编译运行成功。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CPM 尝试 clone Catch2 失败 | 默认 BUILD_TESTING=ON 时 test/ 目录通过 CPM 拉取 Catch2 | 设置 -DBUILD_TESTING=OFF |

## 源码修改

无修改。libmcfp v1.4.2 在 HarmonyOS 上直接可用，无需任何平台适配补丁。

## 软件信息
- 类型: header-only INTERFACE 库
- 语言: C++20
- 许可证: BSD-2-Clause
- 依赖: 无（v1.4.2 无外部依赖）
- 头文件路径: include/mcfp/
- 主要头文件: mcfp/mcfp.hpp（包含全部 API）
---

**编译结束**: 2026-09-10 15:55
**最终状态**: published
