# SDL3

Simple DirectMedia Layer 3 - 跨平台多媒体库

## 简介

SDL3 是 Simple DirectMedia Layer 的最新版本，提供跨平台访问音频、键盘、鼠标、joystick 和图形硬件的低级 API。

## 特性

- 音频输入/输出
- 2D 图形渲染
- 多线程支持
- 文件系统抽象
- 游戏控制器支持

## 依赖

- CMake >= 3.16
- Clang 编译器

## HarmonyOS 适配

- 添加平台检测：`__OHOS__` 宏定义
- 禁用 Gtk 相关功能（SDL_TRAY）
- 禁用 pthread 线程取消功能（HarmonyOS pthread 实现不完整）
- 定义 SDL_PLATFORM_OHOS 平台标识

## 编译状态

- 版本：3.4.8
- 构建系统：CMake
- 编译器：Clang
- 平台：HarmonyOS aarch64
- 状态：built（编译成功）

## 使用方法

预编译包可通过 cmd-pkgs 公共安装脚本安装：
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- sdl3 3.4.8
```

安装后，库文件位于 `~/usr/local/lib/libSDL3.so`。