# sdl2_net

SDL2 networking library.

## 描述

SDL2_net 是 SDL2 的网络扩展库，提供简单的网络通信功能。

## 编译版本

- 2.2.0

## 依赖

- SDL2 2.30.0

## 编译说明

使用 CMake 构建系统（避开 autotools 在 OpenHarmony 上的临时文件权限问题）。

## 平台适配

- config.guess: 添加 HarmonyOS 平台识别
- config.sub: 添加 ohos 系统支持

## 产物

- libSDL2_net.so: 网络库
