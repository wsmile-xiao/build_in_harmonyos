# OpenJPEG for HarmonyOS

## 概述

OpenJPEG 是 JPEG 2000 标准的开源实现，包含编解码库和命令行工具。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | openjpeg |
| 版本 | 2.5.4 |
| 官方仓库 | https://github.com/uclouvain/openjpeg |
| 许可证 | BSD-2-Clause |
| 构建系统 | CMake |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS HongMeng Kernel |
| 架构 | aarch64 |
| 编译器 | clang (LLVM 15.0.4) |

## 构建产物

- `libopenjp2.so` — 共享库
- `libopenjp2.a` — 静态库
- `opj_compress` — JPEG 2000 编码器
- `opj_decompress` — JPEG 2000 解码器
- `opj_dump` — JPEG 2000 信息查看工具

## 适配要点

1. CMake 构建系统，无需补丁即可在 OHOS 上编译
2. 需要设置 `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG="-Wl,-soname,"` 以修复 OHOS 上的 SONAME 缺失问题
3. 默认构建共享库 (`BUILD_SHARED_LIBS=ON`)
4. 无外部依赖（zlib/tiff/lcms2 可选，缺失时跳过相关功能）
