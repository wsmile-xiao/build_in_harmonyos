# SDL2

## 简介

SDL2（Simple DirectMedia Layer 2）是一个跨平台的多媒体库，提供音频、键盘、鼠标、游戏控制器和图形硬件的低级访问接口。

## 版本

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| 2.30.0 | published | 2026-05-19 |

## 依赖

- 无外部依赖（自包含库）

## 编译说明

SDL2 使用 CMake 构建，支持 autotools 作为备选方案。

### HarmonyOS 平台适配

- E051: `pthread_setcanceltype` syscall 缺失，需在 `SDL_systhread.c` 添加 `#ifndef __OHOS__` 守卫
- E092: CMake 设置 `CMAKE_SYSTEM_NAME=Linux` 绕过平台检测

## 使用方法

```bash
# pkg-config
pkg-config --cflags sdl2
pkg-config --libs sdl2

# sdl2-config
sdl2-config --version
sdl2-config --cflags
sdl2-config --libs
```

## 相关链接

- 官网: https://www.libsdl.org/
- 源码: https://github.com/libsdl-org/SDL
