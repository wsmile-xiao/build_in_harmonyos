# ccache

ccache 是一个 C/C++ 编译器缓存工具，通过缓存编译结果来加速重新编译。

## 功能概述

- 缓存 C/C++ 编译结果，避免重复编译
- 透明集成，可作为编译器包装器使用
- 支持多种编译器（GCC、Clang、MSVC）
- 统计信息查看和缓存管理

## OHOS 适配

- 构建系统为 cmake，需要 2 个平台适配补丁
- 补丁 0001: Makefile 适配
- 补丁 0002: configure 脚本适配

## 依赖关系

- C++ 编译器
- CMake（构建工具）

## 参考资料

- 官网: https://ccache.dev/
- 源码: https://github.com/ccache/ccache
