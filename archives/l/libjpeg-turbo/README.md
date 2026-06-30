# libjpeg-turbo

## 简介

libjpeg-turbo 是一个 JPEG 图像编解码库，使用 SIMD 指令（MMX、SSE2、AVX2、NEON）加速 baseline 和 progressive JPEG 压缩和解压缩。在支持 SIMD 的系统上，libjpeg-turbo 通常比 libjpeg 快 2-6倍。

## 功能概述

- **JPEG 编解码**：支持 baseline 和 progressive JPEG
- **SIMD 加速**：x86 (MMX/SSE2/AVX2) 和 ARM (NEON) 平台优化
- **颜色空间扩展**：支持 RGBX、XBGR 等 32 位和大端像素缓冲区
- **TurboJPEG API**：更简单直接的 API 接口
- **Java 接口**：完整的 Java 绑定支持

## OHOS 适配

### 适配要点

1. **SIMD 支持问题**：由于 HarmonyOS 平台识别问题，SIMD 模块编译会失败，需要通过 `-DWITH_SIMD=0` 禁用
2. **CMake 平台检测**：CMake 无法识别 HarmonyOS 系统，但可以通过禁用 SIMD 绕过
3. **静态库编译**：编译为静态库和动态库，提供 libjpeg 和 TurboJPEG 两种 API

### 已知问题

- E096: SIMD 链接失败（未知平台），需禁用 SIMD
- CMake 平台检测失败，但不影响核心功能

## 依赖

### 编译依赖

- CMake 3.5+
- C 编译器 (clang)

### 无外部库依赖

libjpeg-turbo 是独立的图像编解码库，不依赖其他图像库。

## 功能验证

```bash
# 验证动态库存在
ls ~/usr/local/lib/libjpeg.so*
ls ~/usr/local/lib/libturbojpeg.so*

# 验证静态库存在
ls ~/usr/local/lib/libjpeg.a
ls ~/usr/local/lib/libturbojpeg.a

# 验证可执行文件
~/usr/local/bin/cjpeg -h
~/usr/local/bin/djpeg -h
~/usr/local/bin/jpegtran -h

# 验证头文件
ls ~/usr/local/include/jpeglib.h
ls ~/usr/local/include/turbojpeg.h
```

## 参考

- 官方网站：https://libjpeg-turbo.org/
- GitHub：https://github.com/libjpeg-turbo/libjpeg-turbo
- 文档：https://libjpeg-turbo.org/Documentation