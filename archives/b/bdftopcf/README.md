# bdftopcf

## 软件说明

bdftopcf 是 X.Org 的字体转换工具，用于将 BDF (Bitmap Distribution Format) 字体文件转换为 PCF (Portable Compiled Format) 格式。PCF 格式是 X Window System 使用的编译后字体格式，具有更快的加载速度。

## 上游

- 官网: https://www.x.org/
- 源码: https://gitlab.freedesktop.org/xorg/util/bdftopcf
- 许可证: MIT (X11)

## 编译版本

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 1.1.2 | built | 2026-06-18 | 首次鸿蒙编译，3个平台适配补丁 |

## 依赖

- xorgproto (提供 xproto + fontsproto 头文件)
- util-macros (提供 xorg-macros m4 宏)
