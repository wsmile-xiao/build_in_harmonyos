# imlib2

## 软件概述

imlib2 是一个通用的图像加载和渲染库，支持多种图像格式。它是 Enlightenment 项目的核心组件之一，提供了高效的图像处理能力。

## 主要特性

- 支持 PNG、ZLIB 等多种图像格式加载
- 内置支持 ARGB、ANI、BMP、ICO、LBM、PNM、QOI、TGA、XBM、XPM 等格式
- 可扩展的 loader/filter 模块系统
- 高效的内存管理和图像缓存

## 编译版本

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|----------|------|
| 1.12.6 | published | 2026-05-22 | 基础功能完整，PNG/ZLIB loader 可用 |

## 依赖

- **必需**：freetype2, libpng, zlib
- **可选**：libjpeg (JPEG), libgif (GIF), libtiff (TIFF), libwebp (WebP), libheif (HEIF)

## 使用方式

通过 cmd-pkgs 公共安装脚本安装：

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- imlib2 1.12.6
```

## 相关链接

- 官方网站：https://enlightenment.org
- 源码下载：https://download.savannah.nongnu.org/releases/imlib2/