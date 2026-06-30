# libxmp

**libxmp** 是一个跨平台的模块音乐播放器库，支持多种模块音乐格式（MOD、XM、S3M、IT 等）。

## 官方网站
- https://libxmp.org
- https://github.com/libxmp/libxmp

## 编译版本
- **4.6.0** (2026-05-22)

## 功能特性
- 支持 100+ 种模块音乐格式
- 提供静态库和动态库
- C 语言 API，易于集成
- 支持 pkg-config 和 CMake 集成

## 依赖项
无外部依赖（自包含）

## 安装方式
- 预编译包: libxmp-4.6.0-ohos-aarch64.tar.gz
- pkg-config: libxmp

## 使用示例
```c
#include <xmp.h>

xmp_context ctx = xmp_create_context();
xmp_load_module(ctx, "test.xm");
xmp_start_player(ctx, 44100, 0);
xmp_play_frame(ctx);
xmp_end_player(ctx);
xmp_release_module(ctx);
xmp_free_context(ctx);
```

## 编译说明
- 构建系统: CMake（autotools 在 HMDFS 上有权限问题）
- 需要补丁: E007 (config.guess/config.sub) - 仅用于 autotools
- 编译器: clang 15.0.4