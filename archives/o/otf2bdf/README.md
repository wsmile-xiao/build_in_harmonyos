# OTF to BDF Converter (otf2bdf)

> 将 OpenType 字体转换为 BDF 字体的工具，使用 FreeType 2 渲染器

## 简介

otf2bdf 是一个将 OpenType 字体（包括 TrueType 和 CFF）转换为 BDF（Bitmap Distribution Format）字体格式的工具。它使用 FreeType 2 库来渲染字形位图，支持多种字符集映射和编码。

该工具主要用于 bitmap 字体生成，在嵌入式系统、游戏开发和老式 X11 应用中仍有使用价值。BDF 字体可以通过 bdftopcf 工具转换为 PCF 格式，供 X Window System 使用。

## OHOS 适配要点

在 HarmonyOS 上编译 otf2bdf 需要注意以下关键问题：

1. **依赖预装**: 需要预先安装 freetype、libpng、zlib 等依赖（可通过 cmd-pkgs 预编译包安装）
2. **pkg-config 设置**: configure 使用 pkg-config 检查 FreeType，需要设置 PKG_CONFIG_PATH
3. **补丁替代**: 原始 configure 脚本使用复杂 autoconf 语法，在 toybox sh 下不兼容，补丁提供简化版本
4. **链接器问题**: 使用 cc wrapper（而非直接 clang）以避免 lld 链接器的 libxml2 依赖问题

## 排除与替代

暂无需要排除的组件。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| freetype | 26.6.20+ | 字体渲染引擎 |
| zlib | 1.3.1+ | 压缩库（freetype 依赖） |
| libpng | 1.6.43+ | PNG 图像库（freetype 依赖） |

## 功能验证

otf2bdf 基本功能验证：

```bash
# 显示帮助信息
otf2bdf -h

# 转换示例字体
otf2bdf -p 12 -r 72 example.ttf -o example-12.bdf

# 查看字体编码表
otf2bdf -et example.ttf
```

## 参考

- [原始 README](http://archive.ubuntu.com/ubuntu/pool/main/o/otf2bdf/)
- [FreeType 官网](https://www.freetype.org/)
- [BDF 字体格式](https://en.wikipedia.org/wiki/Glyph_Bitmap_Distribution_Format)