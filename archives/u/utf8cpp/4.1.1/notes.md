# utf8cpp 4.1.1 适配笔记

## 编译环境
- 构建系统: cmake（header-only INTERFACE library）
- 编译日期: 2026-07-14
- 编译器: clang/clang++
- 状态: built

## 软件简介

utf8cpp（UTF8-CPP）是一个 C++ 可移植 UTF-8 编解码库，提供高效、安全、易用的 UTF-8 字符串操作接口。支持 UTF-8 与 UTF-16/UTF-32 互转、字符迭代、字符串校验、无效序列替换等功能。

## 构建选项

| 选项 | 值 | 说明 |
|------|-----|------|
| UTF8CPP_ENABLE_TESTS | ON | 集成上游测试 (6 个 CTest 用例) |
| UTF8CPP_ENABLE_BENCHMARKS | OFF | 不编译基准测试 |

## 依赖

无任何依赖，仅包含头文件。

## 编译步骤

1. **源码下载**: 从 GitHub 下载 utf8cpp v4.1.1
   - URL: https://github.com/nemtrif/utfcpp/archive/refs/tags/v4.1.1.tar.gz
   - SHA256: 1ca68016f0abc24172998e39ce0d8f8e2b7a26f7579a0ff85d4e1b9a7aea56f8

2. **CMake 配置**:
   ```bash
   cmake .. -DCMAKE_SYSTEM_NAME=Linux -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
            -DUTF8CPP_ENABLE_TESTS=ON -DUTF8CPP_ENABLE_BENCHMARKS=OFF
   ```

3. **编译**: INTERFACE library，无需实际编译
   ```bash
   cmake --build .
   ```

4. **安装**: 安装头文件和 CMake 配置
   ```bash
   cmake --install .
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 不识别 OHOS 平台 | 鸿蒙不在 CMake 已知平台列表 | 设置 CMAKE_SYSTEM_NAME=Linux + CMAKE_SYSTEM_PROCESSOR=aarch64（E092 规避） |

## 源码修改

无补丁，header-only 库直接使用源码。

## 交付物

| 文件 | 说明 |
|------|------|
| include/utf8cpp/utf8.h | 主头文件 |
| include/utf8cpp/utf8/*.h | 分模块头文件（core、checked、unchecked、unguarded） |
| lib/cmake/utf8cpp/utf8cppConfig.cmake | CMake 配置文件 |
| lib/cmake/utf8cpp/utf8cppTargets.cmake | CMake 目标文件 |

## 注意事项

1. **Header-only 库**: utf8cpp 是 INTERFACE library，无需编译二进制文件
2. **无依赖**: 不依赖任何第三方库
3. **C++ 标准**: 支持 C++11/14/17/20
4. **头文件路径**: 安装到 `include/utf8cpp/`，包含时使用 `#include <utf8cpp/utf8.h>`
5. **CMake 目标**: `utf8cpp::utf8cpp`
6. **真机验证**: 已在 OHOS 6.0 aarch64 真机 CI 环境验证通过（上游 6 个 CTest 用例 + test_package 7 个断言全部通过）

---

**最终状态**: built
