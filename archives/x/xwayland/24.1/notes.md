# XWayland 24.1 编译笔记

## 编译日期
2026-05-30

## 源码位置
- 使用 xorg-server-21.1.15 源码编译
- 启用 XWayland 模块

## 编译环境
- OpenHarmony
- TMPDIR=/data/storage/el2/base/cache
- 编译器: clang

## 依赖
- wayland
- wayland-protocols
- libXfont2
- pixman
- libdrm
- xkeyboard-config

## 测试验证
✅ Xwayland 二进制编译成功
✅ 可作为 Wayland 合成器的 X server

## 预编译包
- xwayland-24.1-ohos-aarch64.tar.gz (8.7M)
- 包含: bin/Xwayland