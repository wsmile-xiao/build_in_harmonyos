# SDL2-compat

## 软件描述

SDL2-compat 是 SDL2 的兼容层，提供与 SDL2 源码和二进制兼容的 API，但底层使用 SDL3 实现。它允许现有 SDL2 程序无需修改即可运行，同时享受 SDL3 的改进。

官方网站：https://www.libsdl.org/

## 编译说明

### 依赖

- SDL3 3.4.8（运行时和编译时都需要）
- cmake >= 3.0
- clang/clang++

### 平台适配

鸿蒙平台无 X11 支持，编译时需禁用：
```bash
cmake -DSDL2COMPAT_TESTS=OFF -DSDL2COMPAT_X11=OFF ..
```

### 编译版本

- 2.32.68（2026-06-08编译）

## 使用说明

sdl2-compat 运行时需要 SDL3 库。安装 sdl2-compat 后，现有的 SDL2 程序可直接运行，无需修改。

## 注意事项

1. 鸿蒙平台无 X11，已禁用相关功能
2. 测试程序依赖 X11，已禁用（不影响主库功能）
3. 运行时需要 SDL3 库支持