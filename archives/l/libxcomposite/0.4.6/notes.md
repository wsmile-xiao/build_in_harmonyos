# libXcomposite 0.4.6 适配笔记

## 概述

X Composite 扩展客户端库，提供窗口重定向（backing store 到 Pixmap）、
subwindow 重定向与 overlay window API。libXcomposite.so.1。

## OHOS 适配要点

- **依赖**：libx11/6.4.0、libxext/6.4.0、xorgproto/2025.1、libxfixes/6.1.0
  （cmd-pkgs track）。libXcomposite 仅链接 `-lX11`；libXfixes 只在编译期
  提供 Xfixes.h（Xcomposite.h 第 49 行 `#include <X11/extensions/Xfixes.h>`）。
- **configure**：硬要求 `compositeproto >= 0.4`（xorgproto 提供）与 `x11`
  pkg-config 模块；`PKG_CHECK_MODULES(XFIXES, xfixes)` 只取头文件。
- **构建系统**：autotools，复用 libxcb/libxi 的 OHOS 工具链模式
  （clang、CONFIG_SHELL、TMPDIR 进 build 目录、-j1、.pc 相对化）。
- **版本**：`-version-number 1:0:0` → libXcomposite.so.1.0.0。
- **配置选项**：`--disable-docs --disable-specs --without-xmlto
  --without-fop --without-xsltproc`（文档工具不可用，跳过 man 生成）。

## 测试

test_package 构建两个无需 X server 的可执行文件：

1. `libxcomposite_api_surface` — 对 libXcomposite.so.1 全部 10 个导出函数
   生成强制活重定位（XComposite*）。
2. `libxcomposite_version_contract` — 校验 COMPOSITE 协议版本常量
   （XCOMPOSITE_MAJOR 0 / XCOMPOSITE_MINOR 4）与 XCOMPOSITE_VERSION 宏。

## 参考

- 官网: https://gitlab.freedesktop.org/xorg/lib/libxcomposite
- 源码: https://xorg.freedesktop.org/archive/individual/lib/libXcomposite-0.4.6.tar.xz
