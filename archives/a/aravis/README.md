# aravis

## 简介

Aravis is a C/GObject vision library for GenICam-based cameras. It supports
GigE Vision cameras, USB3 Vision cameras through libusb, fake cameras for
tests, and optional GStreamer/GTK integration. The first OpenHarmony package
scope keeps the core library and fake/GigE-oriented validation path, while USB
support is left for a follow-up after `libusb/1.0.27` has a consumable Conan
recipe/package.

This archive tracks the OpenHarmony PC adaptation of aravis 0.8.36.

## 基本信息

| 项目 | 值 |
|------|-----|
| 版本 | 0.8.36 |
| 构建系统 | meson |
| 许可证 | LGPL-2.1-or-later |
| 主页 | https://github.com/AravisProject/aravis |
| 上游源码 | https://github.com/AravisProject/aravis/releases/download/0.8.36/aravis-0.8.36.tar.xz |

## 适配范围

Initial recipe scope:

- Core `libaravis-0.8` library.
- Upstream C tests through `meson.test()`.
- Consumer test using version APIs and the fake device/genicam path.

Disabled in the initial recipe:

- USB3 Vision support, because the current checkout has historical
  `libusb/1.0.27` metadata/patches but no consumable Conan recipe/package on
  the OHOS remote used by local CI precheck.
- GTK viewer, to keep the first pass focused on the core camera library and
  avoid pulling the full GUI dependency path into the initial validation.
- GStreamer plugin, because the current `gstreamer/1.28.3` archive only has
  metadata/notes and no CI input recipe in this checkout.
- Introspection and documentation, to avoid `gobject-introspection` and
  `gi-docgen` build-time dependencies for the first adaptation pass.
- Linux packet socket support, because OpenHarmony is not Linux and the Meson
  option is Linux-specific.

## 高难点

- USB3 Vision support depends on libusb. The current default package disables
  that path until `libusb/1.0.27` is available through Conan, and the local
  historical libusb notes still indicate device-I/O permission limits on
  OpenHarmony application domains.
- Full camera validation requires real GigE/USB3 Vision hardware. The first
  automated validation therefore uses upstream fake camera tests and consumer
  fake-device API checks.
- Optional GUI/multimedia paths depend on GTK and GStreamer packaging status.
