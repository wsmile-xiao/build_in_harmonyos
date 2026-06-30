# woff2

WOFF 2.0 字体压缩库，由 Google 开发。

## 描述

woff2 是一个用于压缩和解压缩 Web Open Font Format (WOFF) 2.0 字体的库。它使用 Brotli 压缩算法，提供了比 WOFF 1.0 更高的压缩率。

## 包含的库

- **libwoff2common**: 共享数据，由 libwoff2dec 和 libwoff2enc 使用
- **libwoff2dec**: WOFF2 解码器库
- **libwoff2enc**: WOFF2 编码器库

## 包含的工具

- **woff2_compress**: 将 TTF 字体压缩为 WOFF2 格式
- **woff2_decompress**: 将 WOFF2 字体解压缩为 TTF 格式
- **woff2_info**: 显示 WOFF2 字体信息

## 依赖

- brotli >= 1.0.0

## 使用方法

```bash
# 压缩字体
woff2_compress myfont.ttf
# 输出: myfont.woff2

# 解压缩字体
woff2_decompress myfont.woff2
# 输出: myfont.ttf

# 查看字体信息
woff2_info myfont.woff2
```

## 编译信息

- 版本: 1.0.2
- 构建系统: CMake
- 编译器: clang++
- 依赖: brotli/1.2.0

## 许可证

MIT License