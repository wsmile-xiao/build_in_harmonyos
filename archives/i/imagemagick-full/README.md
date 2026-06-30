# ImageMagick (full)

ImageMagick 是一个功能强大的图像处理套件，支持创建、编辑、合成和转换位图图像。

## 描述

ImageMagick-full 包含完整的 ImageMagick 功能，支持超过 200 种图像格式（包括 DPX、EXR、GIF、JPEG、JPEG-2000、PDF、PNG、TIFF 等）。提供 magick 命令行工具和 C/C++ API。

## 已编译版本
- 7.1.2-23 (2026-05-26)

## 依赖
- libjpeg-turbo 4.1.1
- libpng 1.6.43
- libtiff 4.6.0
- freetype2 26.20.6
- fontconfig 2.16.0
- libopenjp2 2.5.0

## 特性
- 200+ 图像格式支持
- 图像转换和编辑
- 批量处理脚本
- C/C++ API（MagickCore, MagickWand）
- HDRI 支持
- 多线程处理

## 使用方法
```bash
# 转换图像格式
magick convert input.png output.jpg

# 查看版本
magick --version

# 识别图像信息
magick identify image.png
```

## 注意事项
- HMDFS 上 config.status 创建临时目录需将 umask 077 改为 022（目录 owner 继承父目录 uid）
- 清理 conf* 时避免使用 glob 模式防止误删 config/ 目录
- 无 webp/heic/xml 预编译依赖，configure 时需禁用对应选项