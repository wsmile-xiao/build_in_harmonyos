# stb_image

## 简介
stb_image 是一个单头文件的 C 语言图像加载库，支持多种图像格式。

## 支持的格式
- JPEG baseline & progressive (12 bpc/arithmetic not supported, same as stock IJG lib)
- PNG 1/2/4/8/16-bit-per-channel
- TGA (not sure what subset, if a subset)
- BMP non-1bpp, non-RLE
- PSD (composited view only, no extra channels, 8/16 bit-per-channel)
- GIF (*comp always reports as 4-channel)
- HDR (radiance rgbE format)
- PIC (Softimage PIC)
- PNM (PPM and PGM binary only)

## 特性
- 易于集成：单个头文件
- 公共领域/MIT 双许可证
- 支持从内存或文件加载
- 支持 16 位通道
- 线程安全（需要定义 STBI_NO_FAILURE_STRINGS）

## 版本历史
- 2.30 (2024-05-31): 修复 gcc 边界检查警告

## 上游仓库
https://github.com/nothings/stb
