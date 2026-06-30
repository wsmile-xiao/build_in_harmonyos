# SDL2_image

## 简介

SDL2_image 是 SDL2 的图像加载扩展库，支持多种图像格式：PNG, JPEG, TIFF, BMP, GIF, WebP, AVIF, JXL, QOI, SVG 等。

## 版本

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| 2.8.0 | published | 2026-05-19 |

## 依赖

- **SDL2** >= 2.0.9（必需）

## 编译说明

SDL2_image 使用 CMake 构建，内置 STB 图像解码器可替代外部图像库依赖。

### HarmonyOS 平台适配

- E092: CMake 设置 `CMAKE_SYSTEM_NAME=Linux` 绕过平台检测
- 使用 `SDL2IMAGE_BACKEND_STB=ON` 避免外部图像库依赖

## 使用方法

```bash
# pkg-config
pkg-config --cflags SDL2_image
pkg-config --libs SDL2_image
```

## 相关链接

- 官网: https://www.libsdl.org/projects/SDL_image/
- 源码: https://github.com/libsdl-org/SDL_image
