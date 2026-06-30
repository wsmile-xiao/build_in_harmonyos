# fbida 项目说明

**重要**: 此归档的实际产物是 **exiftran** 工具。

## 项目背景

- **源码包**: fbida-2.14.tar.gz
- **项目作者**: Gerd Hoffmann
- **项目地址**: https://www.kraxel.org/blog/linux/fbida/

fbida 项目包含多个图像处理工具：
- **fbi** - Linux framebuffer 控制台的图像查看器
- **ida** - X11 图像查看和编辑应用（Motif based）
- **exiftran** - JPEG 图像无损转换工具（保留 EXIF 数据）
- **thumbnail.cgi** - CGI 脚本，提取 JPEG EXIF 缩略图

## 本次编译内容

本归档只编译了 **exiftran** 工具，因为：
1. 用户请求编译 exiftran
2. exiftran 没有独立的源码包
3. fbi/ida/fbpdf 需要额外依赖（libdrm、freetype、fontconfig、poppler-glib 等）

## 预编译包

| 版本 | 产物名称 | 内容 |
|------|---------|------|
| 2.14 | exiftran-2.14-ohos-aarch64.tar.gz | exiftran 可执行文件 + man page + 依赖库 |

## 安装方式

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- exiftran 2.14
exiftran -h
```

## 工具用法

exiftran 用于 JPEG 图像的无损转换（旋转、翻转等），会保留 EXIF 元数据：

```bash
# 自动根据 EXIF 方向标签旋转
exiftran -a image.jpg

# 旋转 90 度
exiftran -9 image.jpg

# 旋转 180 度
exiftran -1 image.jpg

# 旋转 270 度
exiftran -2 image.jpg
```

## 相关文档

- [exiftran man page](2.14/packaging/share/man/man1/exiftran.1)
- [编译笔记](2.14/notes.md)
- [编译配置](2.14/manifest.yaml)