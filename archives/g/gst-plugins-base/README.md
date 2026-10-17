# GStreamer Base Plugins for HarmonyOS

## 概述

GStreamer Base Plugins 在 HarmonyOS/OpenHarmony (aarch64) 上的编译和测试记录。

**可用版本**:
- **1.28.3** (最新稳定版): 使用 meson 构建系统，需修复 Python 脚本执行问题

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | GStreamer Base Plugins |
| 官网 | https://gstreamer.freedesktop.org/ |
| 下载 | https://gstreamer.freedesktop.org/src/gst-plugins-base/ |
| 许可证 | LGPL |

## 版本状态

| 版本 | 状态 | 构建系统 | 备注 |
|------|------|----------|------|
| 1.28.3 | built | meson | 最新稳定版，需修复 Python 脚本执行，创建 pkg-config wrappers |

## GStreamer Base Plugins 1.28.3 编译

### 依赖

| 依赖 | 版本 | 状态 | 用途 |
|------|------|------|------|
| gstreamer | 1.28.3 | ✅ 已发布 | 核心框架 |
| glib2 | 2.88.0 | ✅ 已发布 | GLib 工具库 |
| orc | 0.4.42 | ✅ 已发布 | 运行时优化 |
| libogg | 1.3.6 | ✅ 已发布 | Ogg 容器格式 |
| libvorbis | 1.3.7 | ✅ 已发布 | Vorbis 音频编解码 |
| opus | 1.5.2.1 | ✅ 已发布 | Opus 音频编解码 |
| alsa-lib | 1.2.16.1 | ✅ 已发布 | ALSA 音频接口 |
| libx11 | 6.4.0 | ✅ 已发布 | X11 窗口系统（ximagesink） |
| libxext | 6.4.0 | ✅ 已发布 | X11 共享内存（xshm） |
| libxv | 1.0.13 | ✅ 已发布 | XVideo（xvimagesink） |
| libxi | 6.1.0 | ✅ 已发布 | XInput2 触摸支持 |
| libdrm | 2.4.133 | ✅ 已发布 | DRM dumb 分配器 |
| iso-codes | 4.20.1 | ✅ 已发布 | 语言代码（gst-tag） |
| pango | - | ❌ 生态冲突 | pango 依赖 glib/2.84.0.1，与 glib2/2.88.0 同图冲突（待生态归一） |
| libtheora | - | ❌ 未发布 | Theora 视频编解码 |
| libvisual | - | ❌ 未发布 | 音频可视化 |
| tremor | - | ❌ 未发布 | 整数 Vorbis 解码 |
| cdparanoia | - | ❌ 未发布 | CD 抓轨 |

> X11 栈版本线说明：libxv/libxi/libxext 均钉 libx11/6.4.0（6.x 版本线），
> 消费方必须使用同一版本线，与 libx11/1.8.13 混用会版本冲突。

### 启用/禁用功能

**启用**: ogg, vorbis, opus, alsa, orc, x11, xshm, xvideo, xi, drm, iso-codes
**禁用（依赖生态缺口，见 notes.md）**: gl, theora, cdparanoia, libvisual, tremor, qt5, pango
**禁用通用选项**: nls, examples, tests, tools, introspection, doc, orc-compiler

### 构建产物（2026-09-17 第二轮）

- 11 个库: gstallocators(含 DRM dumb 分配器), gstapp, gstaudio, gstfft, gstpbutils, gstriff, gstrtp, gstrtsp, gstsdp, gsttag(含 iso-codes 语言名), gstvideo
- 29 个插件: 23 个基础插件 + ogg/vorbis/opus/alsa + ximagesink/xvimagesink
- 40 .a / 41 .pc / 138 .h

### 关键适配点

1. **Python 脚本执行**
   - HMDFS/SELinux 环境下 Python 脚本无法直接执行
   - 需修改 meson.build，使用 python3 解释器调用 meson-pkg-config-file-fixup 和 extract-release-date 脚本

2. **pkg-config wrapper 文件**
   - glib2 conan 包不提供 gobject-2.0.pc, gio-2.0.pc 等子包 .pc 文件
   - gstreamer conan 包不提供 gstreamer-1.0.pc, gstreamer-base-1.0.pc 等子包 .pc 文件
   - 需在 generate() 中创建 wrapper .pc 文件
   - orc 需创建 orc-0.4.pc, libogg 需创建 ogg.pc, libvorbis 需创建 vorbis.pc/vorbisenc.pc, alsa-lib 需创建 alsa.pc

3. **NLS 禁用**
   - OHOS 无 gettext，通过 c_args stub gettext/ngettext 宏

4. **AR/AS/STRIP/NM/RANLIB**
   - CI worker 导出 llvm-* 名称不在 PATH 中，需通过绝对路径 pin
