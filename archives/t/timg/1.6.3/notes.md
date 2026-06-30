# timg 1.6.3 编译笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-25
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 安装依赖预编译包: libdeflate 1.21, libsixel 1.10.5 (从 cmd-pkgs 安装)
2. 创建 libsixel.so 软链接 (HMDFS 不支持 ln -sf)
3. cmake 配置,禁用缺少依赖的功能:
```bash
cmake -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
  -DWITH_VIDEO_DECODING=OFF \
  -DWITH_VIDEO_DEVICE=OFF \
  -DWITH_GRAPHICSMAGICK=OFF \
  -DWITH_TURBOJPEG=OFF \
  -DWITH_RSVG=OFF \
  -DWITH_POPPLER=OFF \
  -DWITH_LIBSIXEL=ON \
  -DWITH_OPENSLIDE_SUPPORT=OFF \
  -DWITH_STB_IMAGE=ON \
  -DWITH_QOI_IMAGE=ON \
  -DTIMG_VERSION_FROM_GIT=OFF \
  ..
```
4. make -j1 编译成功
5. make install DESTDIR=$TEST_PREFIX 安装到 staging 目录

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmake 找不到 libdeflate | libdeflate 未安装 | 从 cmd-pkgs 安装 libdeflate 1.21 |
| 2 | 链接失败 -lsixel not found | libsixel.so 软链接缺失 | 安装 libsixel 后手动创建 .so 软链接 |
| 3 | 多个功能依赖缺失 | ffmpeg/GraphicsMagick++/libexif/librsvg/poppler-glib 无预编译包 | 禁用对应功能,使用 STB 内置解码器作为 fallback |

## 依赖版本

- libdeflate 1.21 (预编译包)
- libsixel 1.10.5 (预编译包)
- STB image (内置 third_party)
- STB resize2 (内置 third_party)
- QOI (内置 third_party)

## 禁用的功能及原因

| 功能 | 原因 |
|------|------|
| WITH_VIDEO_DECODING | 无 ffmpeg/libavcodec 预编译包 |
| WITH_VIDEO_DEVICE | 无 ffmpeg 预编译包 |
| WITH_GRAPHICSMAGICK | 无 GraphicsMagick++ 预编译包 (有 ImageMagick++ 但 timg 要求 GraphicsMagick++) |
| WITH_TURBOJPEG | 需要同时有 libturbojpeg 和 libexif, libexif 无预编译包 |
| WITH_RSVG | 无 librsvg-2.0 预编译包 |
| WITH_POPPLER | 无 poppler-glib 预编译包 (有 poppler-cpp 但 timg 需要 poppler-glib) |
| WITH_OPENSLIDE_SUPPORT | 默认关闭,无 openslide 预编译包 |

## 验证结果

```bash
$ timg --version
timg 1.6.3+  <https://timg.sh/>
Copyright (c) 2016..2024 Henner Zeller. This program is free software; license GPL 2.0.

QOI image loading
STB image loading
Resize: STB resize
Libsixel version 1.10.5
libdeflate 1.21
Half, quarter, iterm2, and kitty graphics output: timg builtin.
```

## 测试报告

ctest: No tests found (timg 无内置测试套件)

## 源码修改

无源码修改,所有功能通过 cmake 选项禁用/启用