# evince 48.4 适配笔记

## 概览

GNOME 文档查看器，48.4 发布版，Meson 构建。本适配面向 HarmonyOS PC (arm64)，
提供 PDF 文档查看功能（poppler 后端），保留 viewer/previewer/thumbnailer。

## 依赖（制品仓版本）

| 依赖 | 版本 | 用途 |
|---|---|---|
| glib | 2.84.0.1 | 核心 GObject 库 |
| gtk | 3.24.43 | UI 工具包 |
| libhandy | 1.8.3 | 自适应部件（需已在制品仓） |
| libxml2 | 2.15.3.1 | XML 解析 |
| gdk-pixbuf | 2.44.6.1 | 图像加载 |
| cairo | 1.18.4 | 2D 渲染 |
| zlib | 1.3.1.1 | 压缩 |
| poppler | 25.12.0.2 | PDF 渲染（poppler-glib） |

## 裁剪

关闭了 OHOS 无对应依赖的功能：dbus、keyring（无 libsecret）、gtk_unix_print、
thumbnail_cache（无 gnome-desktop）、multimedia、gspell（无 gspell）、
introspection、gtk_doc、user_doc、nautilus，以及 comics/djvu/dvi/ps/tiff/xps
后端（制品仓缺 djvulibre/libspectre/libgxps 等）。

## 补丁

- `0001-ohos-portability.patch`：顶层 meson.build 三处 OHOS 适配
  1. `gmodule-no-export-2.0` → `gmodule-2.0`（glib 配方无 gmodule-no-export-2.0 组件，PkgConfigDeps 不生成对应 .pc）
  2. 移除 `gdk_pixbuf_binary_version` 的 get_variable（gdk-pixbuf-2.0.pc 缺该变量）
  3. `cc.find_library('z')` → `dependency('zlib')`（走 PkgConfigDeps 的 zlib.pc）

## 构建

```bash
conan create . -pr:h=../../../../ci/conan/profiles/ohos-aarch64 \
               -pr:b=../../../../ci/conan/profiles/ohos-aarch64 \
               --build=evince/*
```

## 测试

上游无自动化测试。test_package 链接 libevdocument3 验证 ABI 可解析。

## 已知问题 / 注意事项

- libevdocument3/libevview3 的 libtool 版本 4.0.0/3.0.0 由 meson.build 顶部常量生成
- 共享库与 bin/ 下可执行文件均需 OHOS 签名（binary-sign-tool）
