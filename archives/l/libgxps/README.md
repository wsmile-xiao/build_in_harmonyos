# libgxps

## 简介
libgxps 是一个基于 GObject 的库，用于处理和渲染 XPS（XML Paper Specification）文档。XPS 是微软开发的文档格式，类似于 PDF。

## 功能特性
- 解析 XPS 文档结构
- 渲染 XPS 页面到 Cairo 图形表面
- 提取文档元数据和属性
- 支持文档结构和链接

## 依赖
- glib-2.0 >= 2.36.0
- cairo >= 1.10.0
- libarchive >= 2.8.0
- freetype2

## 可选依赖
- lcms2 (色彩管理)
- libjpeg (JPEG 图像支持)
- libtiff (TIFF 图像支持)

## 工具
- xpstopng: 将 XPS 文档转换为 PNG 图像

## 许可证
LGPL-2.1+

## 官方主页
https://gitlab.gnome.org/GNOME/libgxps