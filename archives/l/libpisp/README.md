# libpisp

## 简介

libpisp 是 Raspberry Pi 的 ISP (Image Signal Processor) 配置生成库，用于配置 Pi 摄像头的图像处理参数。

## 功能概述

- ISP 配置生成（backend、frontend）
- 支持多种图像处理算法（tiling 等）
- 提供 JSON 配置文件解析
- 支持 Pi 的多种摄像头变体
- C++ 实现，提供 C 风格 API

## OHOS 适配要点

1. **musl pthread 限制**：musl libc 不支持 `pthread_mutexattr_setrobust`，需添加 `#ifdef __OHOS__` 守卫排除
2. **std::size_t 缺失**：musl C++ 头文件不提供 `std::size_t`，需全局替换为 `size_t`
3. **meson 构建**：需要显式设置 CC、CXX、AR、RANLIB 环境变量（编译器在 ~/usr/local/bin）
4. **meson 编译器检测**：可能需要手动指定编译器路径

## 依赖关系

- **编译依赖**：meson >= 0.50, ninja
- **运行依赖**：无外部依赖

## 参考资料

- GitHub：https://github.com/raspberrypi/libpisp