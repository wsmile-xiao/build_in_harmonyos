# libclapper

## 是什么

Clapper 播放器的核心播放库 `libclapper-0.0`，基于 GStreamer + GLib/GObject 的现代媒体播放内核。
上游 Clapper 是一个面向 GNOME 的现代媒体播放器，其代码库由两个库组成：本库（Clapper 播放库）与
ClapperGtk（GTK 集成库）。本适配只构建播放库。

- 上游仓库：https://github.com/Rafostar/clapper
- 上游文档：https://rafostar.github.io/clapper/doc/clapper/
- 许可证：LGPL-2.1-or-later（应用与 ClapperGtk 之外的库部分）

## 功能概述

- 基于 GStreamer playbin 的播放管线封装：媒体加载、播放/暂停/定位/逐帧、音量/静音/倍速
- 媒体信息模块：媒体项、音/视频/字幕流、时间线标记（Marker）、缩略图 Harvest、提取器（Extractable）
- 队列管理与播放列表解析接口（Playlistable）
- 增强器（Enhancer）代理与 reactable 机制（0.10 新增）

## OHOS 适配要点

- **只构建核心 clapper 库**：Clapper 是单体仓库（库 + ClapperGtk + 应用 + GStreamer 插件），
  meson feature 选项可精确裁剪，`-Dclapper=enabled`、其余 `disabled`。
- 核心库需要 `glib2/gstreamer/gst-plugins-base`，且 registry 这三者不带标准 pkg-config，配方需
  手写 `.pc` wrapper（`gstreamer-audio/tag/pbutils` 由 gst-plugins-base 提供）。
- 核心库不需要 gst-gl / GTK4 / OpenGL（gst-gl 仅在 clappersink GL 插件用到，本配方不构建）。
- 可选/废弃功能全部关闭：enhancers-loader（libpeas-2 未发布）、discoverer/mpris/server。
- 真机无 GStreamer 插件（playbin 等）时，不能构建真实 ClapperPlayer；test_package 用
  init/版本/ClapperMarker 对象做确定性验证，不依赖插件。

## 依赖关系

- 编译依赖：glib2/2.88.0、gstreamer/1.28.3、gst-plugins-base/1.28.3
- 运行依赖：上述 glib/gstreamer 动态库

## 参考资料

- 上游仓库：https://github.com/Rafostar/clapper
- Clapper 播放库 API 文档：https://rafostar.github.io/clapper/doc/clapper/
- 上游发布信息：https://github.com/Rafostar/clapper/releases/tag/0.10.0
