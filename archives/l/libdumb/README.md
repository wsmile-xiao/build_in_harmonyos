# libdumb

## 简介
libdumb(Dynamic Universal Music Bibliotheque)是 IT/XM/S3M/MOD 跟踪器音乐格式的
C 解码库,游戏音频生态(doom 系、GStreamer 插件、Kodi audiodecoder)广泛使用。

## OHOS 适配
- **构建系统**: CMake(上游 kode54/dumb fork;原 katajakasa 上游已消失)
- **依赖链**: 无(仅 libc/libm;allegro4/examples 关闭后零第三方)
- **上游仓库**: https://github.com/kode54/dumb
- **版本索引**:
  - 2.0.3 — 2026-09-29 适配(kode54 tag 2.0.3;aarch64 关 USE_SSE/allegro4/examples;CMake 最低版 3.1 需 policy 注入)
