# libgexiv2

## 简介

gexiv2 是 [Exiv2](https://exiv2.org/) 的 **GObject 封装库**，用于读写图片元数据
（EXIF / IPTC / XMP）。库本体是 C++17 实现（`gexiv2/` 下 10 个 `.cpp`），对外暴露
C ABI（`gexiv2_metadata_*`）与 GObject 类型；GNOME 生态（如 shotwell、gthumb、
GIMP 插件）通过它访问图片元数据。

- 上游仓库：https://gitlab.gnome.org/GNOME/gexiv2
- 构建系统：Meson（`meson_version >= 0.56`）+ Ninja
- 许可：GPL-2.0-or-later

## OHOS 适配

- **构建系统**：Meson 交叉/原生构建，`wrap_mode=nodownload`，C++17（`cpp_std=c++17`）。
- **依赖**：上游 `meson.build` 直接依赖只有两项 —— `dependency('exiv2', '>= 0.26')`
  与 `gobject-2.0` / `gio-2.0`（`>= 2.46.0`，同一个 glib 包提供）。
  glib 选 **2.84.0.1**：`glib/2.88.x` 要求 zlib/1.3.2，与 `exiv2/0.28.7` 钉死的
  `zlib/1.3.1.1` 冲突（conan 报 `Version conflict`）。
- **pkg-config 变量补齐**：`gnome.mkenums()` 会向 `glib-2.0` 索取 `glib_mkenums`
  变量定位 `glib-mkenums` 程序；Conan `PkgConfigDeps` 生成的 `.pc` 只有标准字段，
  需在配方内把 `glib_mkenums` / `glib_genmarshal` 按包内绝对路径补回
  （与 `gupnp-av/0.14.5`、`atk/2.38.0.1.1` 同款）。
- **OHOS 签名**：安装后的 `libgexiv2.so.2.14.6` 必须用
  `/data/service/hnp/bin/binary-sign-tool sign -selfSign 1` 签名，否则动态加载器
  拒载（`dlopen` 报 `Error loading shared library libgexiv2.so.2: Permission denied`）；
  soname 链接 `libgexiv2.so.2` / `libgexiv2.so` 在 OHOS 上落为**真实文件副本**，
  与 `gdk-pixbuf/2.44.6` 的 OHOS 处理一致。
- **特性裁剪**：`introspection` / `vapi` / `python3` / `tools` 全部关闭。提供
  `g-ir-scanner` 的唯一包 `gobject-introspection/1.78.1.1` 的强制版本闭包
  （`glib/2.84.0.1`、`python/3.12.9` 在 `force=True` 的
  `zlib/1.3.1.1.1.1` + `libffi/3.5.2` 下）在 ohpcd 制品仓**没有已发布二进制**，
  属 R36 依赖阻塞。`gtk_doc` 上游默认关闭且制品仓无 gtk-doc，保持关闭。
  `tests=true`（上游默认 false）以便实际执行上游测试。

## 用法

```bash
conan install --requires=libgexiv2/0.14.6 -r=ohpcd
```

`gexiv2.pc` 提供 `-I${includedir}` 与 `-lgexiv2`：

```c
#include <gexiv2/gexiv2.h>

gexiv2_initialize();
GExiv2Metadata *md = gexiv2_metadata_new();
gexiv2_metadata_open_path(md, "photo.jpg", NULL);
const gchar *mime = gexiv2_metadata_get_mime_type(md);   /* (transfer none) */
```

> ⚠️ `gexiv2_metadata_get_mime_type()` 返回内部指针（`transfer none`），
> 不得 `g_free`；`gexiv2_metadata_get_tag_string()` 是 `transfer full`，需要 `g_free`。

## 版本

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 0.14.6 | built | 2026-09-21 | 首次适配（Meson + exiv2/0.28.7 + glib/2.84.0.1） |

## 参考

- 官网 / 仓库：https://gitlab.gnome.org/GNOME/gexiv2
- 源码发布：https://download.gnome.org/sources/gexiv2/0.14/
