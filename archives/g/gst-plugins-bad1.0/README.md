# gst-plugins-bad1.0 for HarmonyOS

## 概述

gst-plugins-bad1.0（GStreamer Bad Plugins，平台任务包名带 1.0 后缀对齐 taskBranch）
在 HarmonyOS/OpenHarmony PC (aarch64) 上的 Conan 配方与适配记录。

**可用版本**:
- **1.28.5**: meson 构建，vendored gst-plugins-base 1.28.5 子项目模式（版本跟进件）

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | GStreamer Bad Plugins (gst-plugins-bad1.0) |
| 官网 | https://gstreamer.freedesktop.org/ |
| 下载 | https://gstreamer.freedesktop.org/src/gst-plugins-bad/ |
| 许可证 | LGPL |

## 版本状态

| 版本 | 状态 | 说明 |
|------|------|------|
| 1.28.5 | built | 1.28.3→1.28.5 版本跟进；vendored base 子项目 |

## 适配要点

- gst-plugins-base 未发布 conan 包：官方 tarball vendor 为 meson subproject
- zlib override 1.3.1.1（PIC）
- glib-mkenums 钉 python3 实现
- meson install 后 ELF 原始产物回写（OHOS 签名）
- 消费端测试 dlopen/dlsym 范式
