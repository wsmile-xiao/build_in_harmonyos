# clang22-ccache

ccache 是一个 C/C++ 编译器缓存工具，通过缓存编译结果来加速重新编译。
本包按赛事命名与 clang 22.1.8 工具链配对，实际上游源码为 ccache 官方
最近稳定版 v4.14（ccache 仓库无 22.1.8 版本号）。

## 功能概述

- 缓存 C/C++ 编译结果，避免重复编译
- 透明集成，可作为编译器包装器使用
- 支持多种编译器（GCC、Clang、MSVC）
- 统计信息查看和缓存管理

## OHOS 适配

- 构建系统为 cmake，直接使用 CMake 构建
- 依赖通过 CMake FetchContent (DEPS=DOWNLOAD) 自动管理，hiredis/xxhash/zstd 预下载
- 存储后端: file, http, redis 全部启用（无裁剪）
- C++20 标准（ccache 4.14 要求）
- 0001-0004 补丁：OHOS libcxx-ohos 未实现 std::ranges 算法，替换为迭代器版

## 依赖关系

- C++ 编译器 (clang 15+)
- CMake 3.18+
- 第三方依赖由 FetchContent 自动下载: blake3, fmt, hiredis, xxhash, zstd, cpphttplib 等

## 参考资料

- 官网: https://ccache.dev/
- 源码: https://github.com/ccache/ccache (tag v4.14)
- 配套组件: https://github.com/llvm/llvm-project (llvmorg-22.1.8)
