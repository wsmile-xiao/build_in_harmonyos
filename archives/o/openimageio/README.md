# OpenImageIO

OpenImageIO 是一个开源的图像输入/输出库，支持读取和写入多种图像格式。

## 描述

OpenImageIO 是一个库，用于读取和写入图像，以及一系列图像相关工具。
它的主要目的是为视觉特效、动画和游戏行业提供简单、统一的图像 I/O API。

## 编译版本

- 3.1.13.1 (2026-05-21)

## 依赖

- zlib
- Imath
- OpenEXR
- libjpeg-turbo
- TIFF
- OpenColorIO
- fmt
- PNG
- WebP

## 使用

```bash
oiiotool --version  # 查看版本
oiiotool input.png -o output.jpg  # 格式转换
```
