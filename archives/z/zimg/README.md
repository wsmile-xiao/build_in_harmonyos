# zimg (z.lib)

## 简介

zimg 是一个图像处理库，实现了常用的图像处理基础功能：
- **缩放**：高保真线性重采样器，包括流行的 Bicubic 和 Lanczos 滤镜
- **色彩空间转换**：支持 SMPTE-C、Rec.709、Rec.2020 等色彩空间
- **深度转换**：支持 BYTE、WORD、HALF、FLOAT 格式，包括抖动方法

## 特性

- 简单 API：支持任意格式之间的转换
- 正确性、灵活性、线程安全
- 高性能：针对 Intel 架构优化，比 swscale 更快

## 编译信息

- 版本：3.0.6
- 构建系统：autotools
- 编译器：clang 15
- 平台：aarch64-unknown-linux-ohos
- 状态：built

## 使用方法

```bash
# 使用 pkg-config 查询编译选项
pkg-config --cflags --libs zimg

# C API 示例
#include <zimg.h>

# C++ API 示例
#include <zimg++.hpp>
```

## 参考链接

- 官方网站：https://github.com/sekrit-twc/zimg
- 文档：见安装目录的 share/doc/zimg/