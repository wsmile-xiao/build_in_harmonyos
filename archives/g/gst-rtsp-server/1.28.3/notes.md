# gst-rtsp-server 1.28.3 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-05-30
- 编译器: clang 15.0.4 / clang++
- 状态: built

## 编译步骤

1. meson setup builddir --prefix=$DEFAULT_PREFIX \
   -Drtspclientsink=enabled \
   -Dexamples=disabled \
   -Dtests=disabled \
   -Dintrospection=disabled \
   -Ddoc=disabled \
   -Dglib_assert=false \
   -Dglib_checks=false
2. ninja -j2 (在 builddir 中)
3. meson install --destdir=$TEST_PREFIX (staging 验证)
4. meson install (安装到本地 prefix)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无 | 构建顺利，无需补丁 | 直接编译即可 |

## 源码修改

无需补丁，源码无需修改即可在 OpenHarmony 平台上编译。

## 依赖版本

- gstreamer 1.28.3
- gst-plugins-base 1.28.3 (含 gst-rtsp, gst-sdp, gst-rtp, gst-net, gst-app, gst-video, gst-pbutils)
- glib 2.88.0 (含 gio-2.0)
- libc (musl)

## 验证结果

```bash
pkg-config --modversion gstreamer-rtsp-server-1.0
# 1.28.3

# 产出库文件
libgstrtspserver-1.0.so.0.2803.0 (1.3MB)
# 产出插件
libgstrtspclientsink.so (317KB)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libgstrtspserver-1.0.so.0.2803.0 | 1.3MB | RTSP 服务端核心库 |
| libgstrtspclientsink.so | 317KB | RTSP 客户端sink插件 |
| gstreamer-rtsp-server-1.0.pc | 495B | pkg-config 文件 |
| 头文件 | 26个 | gst/rtsp-server/ 目录 |

## 注意事项

- gst-rtsp-server 依赖 gst-plugins-base 1.28.3 中的 gst-rtsp/gst-sdp/gst-rtp/gst-net 库
- meson >= 1.4 是必需的（当前有 1.11.1）
- 无需平台适配补丁，原生支持 aarch64 + musl 构建
---

**编译结束**: 2026-06-03 23:59
**最终状态**: built
