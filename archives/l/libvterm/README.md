# libvterm

## 简介

libvterm 是一个抽象的终端模拟器库，提供终端状态机和屏幕缓冲区的实现。它将终端的 VT100/VT220/XTERM escape 序列解析为屏幕状态变化。

## 功能特性

- 终端状态机实现
- 屏幕缓冲区管理
- VT100/VT220/XTERM escape 序列解析
- 支持键盘和鼠标事件处理
- 提供辅助工具：unterm, vterm-ctrl, vterm-dump

## 编译版本

### 0.3.3

- **状态**: published
- **编译日期**: 2026-05-26
- **构建系统**: Makefile (libtool)
- **编译器**: clang

## 安装

通过 cmd-pkgs 公共安装脚本安装预编译包：

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libvterm 0.3.3
```

## 使用

编译完成后，库文件安装到：
- 头文件: `$PREFIX/include/vterm.h`, `$PREFIX/include/vterm_keycodes.h`
- 库文件: `$PREFIX/lib/libvterm.a`, `$PREFIX/lib/libvterm.so`
- pkg-config: `$PREFIX/lib/pkgconfig/vterm.pc`
- 辅助工具: `$PREFIX/bin/unterm`, `$PREFIX/bin/vterm-ctrl`, `$PREFIX/bin/vterm-dump`

## 注意事项

本项目为纯 Makefile 项目，无需 configure 步骤。