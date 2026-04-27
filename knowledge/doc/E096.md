# E081: CMake C++ 标准自动检测失败需显式设置 CMAKE_CXX_STANDARD

## 问题现象

在 OpenHarmony 平台上使用 CMake 编译需要特定 C++ 标准的项目时，遇到以下错误：

```
-- System is unknown to cmake
-- Performing Test ABSL_INTERNAL_AT_LEAST_CXX17 - Failed
CMake Error at CMake/AbseilDll.cmake:745 (message):
  The compiler defaults to or is configured for C++ < 17.
  C++ >= 17 is required and Abseil and all libraries that use Abseil must use the same C++ language standard
```

## 根因分析

OpenHarmony 平台上 CMake 无法正确识别系统类型，导致编译器特性检测失败。即使编译器（clang++）实际支持 C++17，CMake 的编译特性检测（如 `ABSL_INTERNAL_AT_LEAST_CXX17`）也会因为平台识别失败而返回 False。

这是 CMake 缺少 OpenHarmony 平台定义文件的问题，与 E007（平台识别）相关。

## 解决方案

显式设置 `CMAKE_CXX_STANDARD` 和 `CMAKE_CXX_STANDARD_REQUIRED` 参数：

```bash
cmake .. \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DCMAKE_CXX_STANDARD=17 \
  -DCMAKE_CXX_STANDARD_REQUIRED=ON
```

## 适用范围

- 所有使用 CMake 且依赖编译特性检测来确定 C++ 标准的项目
- 特别是要求特定 C++ 标准的库：
  - abseil-cpp（要求 C++17）
  - 其他现代 C++ 库

## 实例

### abseil-cpp 20260107.1

```bash
# 错误情况
cmake ..
# → CMake Error: C++ >= 17 is required

# 修复方案
cmake .. -DCMAKE_CXX_STANDARD=17 -DCMAKE_CXX_STANDARD_REQUIRED=ON
# → 配置成功
```

## 关联知识

- E007: 平台识别失败（config.guess/config.sub）
- R1: 参数最少化原则

## 注意事项

1. `CMAKE_CXX_STANDARD` 必须是有效的整数年份（11, 14, 17, 20 等）
2. 对于 C++20 项目，使用 `-DCMAKE_CXX_STANDARD=20`
3. 设置 `CMAKE_CXX_STANDARD_REQUIRED=ON` 确保编译器必须支持指定标准

---

**发现于**: abseil-cpp 20260107.1 编译  
**日期**: 2026-04-23  
**贡献者**: 0D0A