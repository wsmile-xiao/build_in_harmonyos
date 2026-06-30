# libvpx - VP8/VP9 Video Codec Library

## 软件描述

libvpx 是 Google 开发的开源视频编解码库，实现 VP8 和 VP9 视频编码格式。
VP8/VP9 是 WebM 项目的一部分，广泛用于 Web 视频流媒体和 WebRTC 应用。

**主要功能**：
- VP8 编解码器（视频压缩）
- VP9 编解码器（更高效的压缩，支持更高分辨率）
- NEON SIMD 优化（ARM 平台）

**用途**：
- WebRTC 视频通信
- WebM 格式视频编码
- FFmpeg、GStreamer 等多媒体框架的后端编解码器

## 版本列表

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|----------|------|
| 1.14.1 | built | 2026-05-29 | G0 验证失败，需环境 hints |

## 构建特性

- **构建系统**：自定义 configure 脚本（非标准 autotools）
- **目标平台**：arm64-linux-gcc
- **产物类型**：静态库 (libvpx.a) + 工具 (vpxenc/vpxdec)
- **优化**：NEON SIMD（自动检测）

## 编译依赖

- clang/clang++（OHOS SDK LLVM）
- make（GNU Make 4.4.1+）
- diff（GNU diffutils）

## 环境要求

编译前必须设置：
```bash
source archives/l/libvpx/hints/environment.sh
```

详见：`archives/l/libvpx/hints/README.md`

## 链接说明

libvpx 编译为静态库，链接时需要：
```bash
# pkg-config 方式
pkg-config --cflags --libs vpx

# 直接链接
-lvpx -lpthread
```

## 文档

- 官方文档：https://www.webmproject.org/docs/
- GitHub：https://github.com/webmproject/libvpx