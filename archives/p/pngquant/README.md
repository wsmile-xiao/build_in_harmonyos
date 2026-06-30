# pngquant

## 简介

pngquant 是一个用于 PNG 图片有损压缩的高质量命令行工具。它使用专用的算法将 PNG 图片中的颜色数量减少到最多 256 种，从而显著减小文件大小，同时保持视觉质量。

## 主要功能

- **有损压缩**：通过减少颜色数量来压缩 PNG 图片
- **高质量**：使用先进的算法保持图片质量
- **速度优化**：支持多线程处理（OpenMP）
- **批量处理**：支持批量压缩多个图片
- **质量控制**：可设置最小和最大质量参数
- **速度选项**：可选择快速或慢速压缩模式

## 技术特点

- 内嵌 libimagequant 库（静态编译）
- 动态链接 libpng16.so 和 zlib
- 支持 SSE 指令优化（可选）
- 支持 OpenMP 多线程（可选）

## 依赖说明

### 必需依赖

- libpng 1.6.43：PNG 图片读写库
- zlib 1.3.1：压缩库（libpng 内置使用）

### 编译依赖

- clang 或 gcc（支持 C99）
- GNU make
- pkg-config

## 安装方法

### 从预编译包安装

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- pngquant 2.18.0
```

### 手动编译

```bash
export CC=clang
export PKG_CONFIG_PATH=/usr/local/lib/pkgconfig
./configure --prefix=/usr/local
make -j2
make install
```

## 使用方法

```bash
# 基本用法
pngquant input.png

# 设置质量范围
pngquant --quality=65-80 input.png

# 批量处理
pngquant *.png

# 强力压缩
pngquant --force --quality=50-80 input.png output.png
```

## 版本信息

- 当前版本：2.18.0
- 发布日期：January 2023
- 官方网站：https://pngquant.org/

## 许可证

pngquant 使用 BSD 许可证。内嵌的 libimagequant 使用 GPLv3 许可证。
