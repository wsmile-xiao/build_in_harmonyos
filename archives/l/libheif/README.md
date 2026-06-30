# libheif

libheif 是一个用于解码和编码 HEIF/HEIC 图像文件格式的库。

## 描述

HEIF (High Efficiency Image Format) 是一种基于 HEVC (H.265) 或 AV1 编码的现代图像格式，由 MPEG 开发。libheif 提供了对 HEIF 文件的读写支持，支持多种编解码器：

- libde265 (HEVC 解码)
- x265 (HEVC 编码)
- AOM/AV1 (AV1 编解码)
- dav1d (AV1 解码)

## 版本

| 版本 | 状态 | 备注 |
|------|------|------|
| 1.18.2 | built | 支持多种编解码器 |

## 依赖

- libde265 (HEVC 解码)
- libaom (AV1 编解码)
- libjpeg-turbo (可选)
- libpng (可选)

## 相关链接

- 官网: https://github.com/strukturag/libheif
- 源码: https://github.com/strukturag/libheif/releases