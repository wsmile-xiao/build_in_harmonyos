# VIPS

## 简介

VIPS（Visual Image Processing System）是一个高性能图像处理库，专为处理大型图像而设计。它采用惰性计算和面向对象的架构，能够高效处理 GB 级图像，内存占用极低。

## 功能概述

- **高效图像处理**：惰性计算架构，只计算实际需要的像素
- **多格式支持**：JPEG, PNG, TIFF, WebP, HEIF, PDF, SVG 等
- **丰富操作**：缩放、裁剪、旋转、色彩调整、滤镜等
- **命令行工具**：vips, vipsedit, vipsheader, vipsthumbnail
- **C++/Python 绑定**：提供 libvips-cpp 和 pyvips

## OHOS 适配

- **构建系统**：meson（非 autotools），需要 ninja 构建工具
- **依赖要求**：glib-2.0 >= 2.88.0（使用 cmd-pkgs 预编译包）
- **可选功能**：gobject-introspection 可禁用（无预编译包）
- **ELF 签名**：预编译包在打包阶段自动签名
- **已知问题**：部分图像格式依赖库（如 OpenJPEG、Highway）无预编译包

## 依赖

### 编译依赖
- glib >= 2.88.0
- libpng
- libjpeg
- meson >= 0.50
- ninja

### 可选依赖
- libtiff
- libexif
- orc
- fftw3
- libheif
- cairo
- pango

## 功能验证

```bash
# 查看版本
vips --version

# 图像信息
vipsheader input.jpg

# 缩放图像
vips resize input.jpg output.jpg 0.5

# 缩略图生成
vipsthumbnail input.jpg -o thumbnail.jpg
```

## 参考

- 官网：https://libvips.github.io/libvips/
- 源码：https://github.com/libvips/libvips
- 文档：https://libvips.github.io/libvips/API/current/