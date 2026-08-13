# CLI11 2.6.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-07
- 编译器: clang/clang++
- 状态: built（HarmonyOS 真机验证通过）
- 特殊说明: header-only 库，无需编译二进制

## 库简介

CLI11 是一个用于 C++11 及以上版本的命令行解析库，提供丰富的功能和简洁的接口。
- 上游仓库: https://github.com/CLIUtils/CLI11
- 许可证: BSD-3-Clause
- 类型: header-only（INTERFACE library）

## Conan 配方说明

### 配方结构
- `conanfile.py`: Conan 配方，使用 CMake 工具链
- `conandata.yml`: 源码下载 URL 和 SHA256
- `test_package/`: 消费者测试，验证 CLI11 头文件可用性

### 关键配置
- `package_type = "header-library"`：声明为纯头文件库
- `package_id` 使用 `self.info.clear()`：所有 settings 组合产出相同包
- `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=str(self.settings.arch)`：规避 E092（CMake 不识别 OHOS）并支持多架构
- `CMAKE_CXX_STANDARD=11` / `CMAKE_CXX_STANDARD_REQUIRED=ON`：固定上游测试使用 C++11
- `BUILD_TESTING=ON` / `CLI11_BUILD_TESTS=ON`：构建并执行完整上游 CTest 测试
- `CLI11_BUILD_EXAMPLES=OFF` / `CLI11_BUILD_DOCS=OFF`：关闭非必要构建目标
- `CLI11_INSTALL=ON`：启用 CMake install 安装头文件和配置

### 平台适配
- R32: `self.settings.os in ("Linux", "OHOS")` 平台判断
- E092: 通过 CMakeToolchain 设置 CMAKE_SYSTEM_NAME=Linux 规避鸿蒙平台未知问题
- OHOS 真机使用 `os.version=5.0`、`compiler.libcxx=libc++` 和 C++11 配置。

## 依赖

CLI11 是 header-only 库，无外部依赖。

## 测试说明

### test_package 测试
- 文件: `test_package/test.cpp`
- 验证内容:
  1. `#include <CLI/CLI.hpp>` 头文件可被包含
  2. `CLI::App` 实例化
  3. 选项添加（`add_option` / `add_flag`）
  4. 命令行解析（`CLI11_PARSE`）及解析结果验证

### 上游测试
- 上游使用 CMake/CTest 框架，测试文件在 `tests/` 目录
- 主配方启用 `BUILD_TESTING=ON` 和 `CLI11_BUILD_TESTS=ON`
- `build()` 在构建完成后调用 `cmake.test()` 执行完整测试集
- Linux/OHOS、C++11、Boost 关闭配置下共生成 24 个上游 CTest 测试程序
- test_package 继续提供 4 个消费者视角烟雾测试断言

## 源码修改

1 个可移植性补丁：`patches/0001-use-local-catch2.patch` — 上游 `tests/CMakeLists.txt` 用 `file(DOWNLOAD ...)` 从 `github.com/philsquared/Catch` 拉 Catch2 v2.13.10 单头文件 `catch.hpp`，CI Worker 网络受限时下载失败导致 CMake configure 报错。本补丁将 `file(DOWNLOAD ...)` 替换为 `configure_file(${CMAKE_CURRENT_SOURCE_DIR}/catch.hpp ... COPYONLY)`，让 CMake 从源码树的 `tests/catch.hpp` 复制到 binary 目录，规避网络下载依赖。`catch.hpp` 由 Conan 配方的 `source()` 阶段从 `conandata.yml` 的 `catch2` 段下载并放置到 `tests/catch.hpp`，文件 SHA256 与上游 CMake 期望值一致：`3725c0f0a75f376a5005dde31ead0feb8f7da7507644c201b814443de8355170`。

## 验证结果

HarmonyOS 真机冷构建通过：上游 CTest 24/24（100%），Conan `test_package` 消费者测试 1/1（4 项断言全部通过）。

## 注意事项

1. **Header-only 库特性**：CLI11 无需编译二进制，只需 CMake 配置和头文件安装
2. **CMake 目标**：安装后可通过 `find_package(CLI11)` 和 `CLI11::CLI11` 目标链接
3. **C++ 标准**：要求 C++11 及以上
4. **无 ELF 签名**：header-only 库无二进制文件，不需要 ELF 签名和 RPATH 设置
