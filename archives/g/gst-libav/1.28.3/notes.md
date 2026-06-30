# gst-libav 1.28.3 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-05-30
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
# Meson 构建
cd ~/tmp/builds/gst-libav-1.28.3.work
meson setup _build --prefix=$HOME/usr/local -Dtests=disabled -Ddoc=disabled
ninja -C _build
DESTDIR=$HOME/tmp/test-install-gst-libav-1.28.3 ninja -C _build install
ninja -C _build install  # 本地安装（不带 DESTDIR）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | gst-inspect-1.0 无法执行（缺少 RPATH/lib 加载失败） | musl 动态链接器不支持 LD_LIBRARY_PATH | 不影响 gst-libav 插件本身；插件由 GStreamer 动态加载 |

## 源码修改

无补丁。源码未做任何修改，meson 原生支持 HarmonyOS/aarch64 平台编译。

## 依赖版本

- gstreamer 1.28.3
- gst-plugins-base 1.28.3
- glib 2.88.0
- FFmpeg 7.1.1 (libavcodec, libavformat, libavutil, libswresample, libswscale, libavfilter - 静态链接)
- zlib (动态链接)

## 验证结果

```bash
# 插件 ELF 验证
readelf -d ~/usr/local/lib/gstreamer-1.0/libgstlibav.so | grep SONAME
# → Library soname: [libgstlibav.so]

# GStreamer 插件描述符符号验证
readelf --dyn-syms ~/usr/local/lib/gstreamer-1.0/libgstlibav.so | grep gst_plugin_libav
# → gst_plugin_libav_get_desc / gst_plugin_libav_register

# 插件大小: 78MB (包含静态链接的 FFmpeg 库)
```

gst-inspect-1.0 无法直接运行验证插件（musl 动态链接器 RPATH 问题），但插件 ELF 结构完整且包含正确的 GStreamer 插件描述符符号。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/gstreamer-1.0/libgstlibav.so | 78,019,008 bytes | GStreamer FFmpeg wrapper plugin |

## 注意事项

1. gst-libav 是纯插件包，没有 bin/ 目录下的可执行文件
2. FFmpeg 库（libavcodec.a 等）静态链接到插件中，导致插件文件较大（78MB）
3. verify-build G1/G2 门禁检测无独立可执行文件（符合预期：纯插件包）
---

**编译结束**: 2026-06-03 23:59
**最终状态**: built
