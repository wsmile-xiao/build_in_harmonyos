# libwpebackend-fdo

WPEWebKit freedesktop.org 后端实现。

## 描述

libwpebackend-fdo 提供 WPEWebKit 与 Wayland 合成器的集成：
- Wayland 显示支持
- EGL 渲染后端
- DMA-BUF 缓冲区共享

## 版本

- 1.15.90 (2026-06-15) - built

## 依赖

- libwpe >= 1.14.0
- libepoxy >= 1.5.0 (需启用 EGL)
- wayland-client
- wayland-server
- glib-2.0

## 编译说明

- 构建系统：meson
- 关键修复：先编译 libepoxy 启用 EGL 支持
- 平台：aarch64-unknown-linux-ohos

## 许可证

BSD-2-Clause