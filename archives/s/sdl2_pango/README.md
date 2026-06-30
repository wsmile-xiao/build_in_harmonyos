# sdl2_pango

SDL2_Pango 是一个用于在 SDL2 应用中渲染 Pango 文本的库。

## 简介

SDL2_Pango 提供了将 Pango 文本布局渲染到 SDL2 表面的功能。Pango 是一个用于布局和渲染国际化文本的库，支持多种语言和复杂的文本布局。

## 编译版本

- **版本**: 2.1.5
- **状态**: built
- **编译日期**: 2026-06-08
- **构建系统**: autotools
- **目标平台**: HarmonyOS aarch64 (musl libc)

## 依赖

- pango >= 1.2.0
- pangoft2 >= 1.2.0
- SDL2 >= 2.0.2

## 补丁说明

| 补丁文件 | 用途 |
|---------|------|
| 0003-config.guess.patch | HarmonyOS 平台识别支持 |
| 0004-config.sub.patch | ohos 三元组验证支持 |

## 遇到的问题

1. **平台识别问题 (E072)**：config.guess/config.sub 不识别 HarmonyOS
   - 解决：在 config.guess 中添加 HarmonyOS 系统检测，在 config.sub 中添加 linux-ohos 映射

2. **HMDFS SELinux 权限问题**：configure 使用 umask 077 无法创建临时文件
   - 解决：修改 configure 中 umask 077 为 umask 022

## 验证结果

- 编译产物：libSDL2_Pango.so.4.1.0（共享库）+ libSDL2_Pango.a（静态库）
- G0 干净构建验证：✅ PASS
- G1 二进制完整性：✅ PASS
- G2 功能可用性：✅ PASS
- G3 可移植性：✅ PASS
- G4 档案完整性：✅ PASS

## 使用方式

```c
#include <SDL2_Pango.h>

// 初始化
SDL2_Pango *context = SDL2_Pango_create();

// 渲染文本
SDL2_Pango_draw_text(context, surface, "Hello, World!", x, y);

// 清理
SDL2_Pango_destroy(context);
```