# DjVuLibre

DjVuLibre 是 DjVu 格式的开源实现，包含编解码器、命令行工具和浏览器插件支持。

## 描述

DjVuLibre 是一个用于 DjVu 格式图像的开源库和工具集。DjVu 是一种针对高分辨率文档图像优化的压缩格式，特别适合扫描文档的存储和分发。

## 已编译版本
- 3.5.29 (2026-05-26)

## 构建系统

autotools

## 依赖
- libjpeg 9e
- libtiff 4.6.0
- zlib 1.3.1

## 特性
- DjVu 文件编码/解码
- 命令行工具：ddjvu, djvm, djvused, djvutxt, bzz, c44, cjb2, cpaldjvu, csepdjvu, djvmcvt, djvudump, djvuextract, djvumake, djvups, djvuserve, djvutoxml, djvuxmlparser
- libdjvulibre 共享库

## 使用方法
```bash
# 将 DjVu 转为其他格式
ddjvu -format=pdf input.djvu output.pdf

# 提取 DjVu 文本
djvutxt input.djvu output.txt

# 查看 DjVu 文件信息
djvused input.djvu -e 'dump'
```

## 注意事项
- configure 需使用 `--disable-desktopfiles`（图标生成依赖 ImageMagick，HarmonyOS 环境不可用）
- configure 自动识别 `linux-ohos` 平台
- iconv 支持检测为 no，但不影响核心 DjVu 功能