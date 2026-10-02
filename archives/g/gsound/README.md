# gsound

GSound — 小型 GNOME 库，用于播放系统声音。基于 GObject Introspection 设计，
是 [libcanberra](http://0pointer.de/lennart/projects/libcanberra/) 的薄封装。

- 上游：https://gitlab.gnome.org/GNOME/gsound
- 构建系统：meson (>= 0.50.0) + ninja
- 许可证：LGPL-2.1-or-later

## 鸿蒙适配要点

1. **依赖栈**：直接依赖 glib2（glib-2.0 / gobject-2.0 / gio-2.0）与 libcanberra。
   不依赖 libsoup3/gssdp/libxml2（与 gssdp/gupnp 不同）。
2. **gnome 模块交叉编译**：`gsound/meson.build` 用 `gnome.mkenums()` 生成枚举代码，
   依赖 glib2 包 `bin/glib-mkenums`（python 脚本）。配方 `generate()` 将其钉入
   meson 原生 `[binaries]` 段（`tc.binaries`），避免 pkg-config 变量回退失败。
3. **glib2 .pc 前缀修复**：glib2 包的 `.pc` 文件以 `prefix=/` 安装（Cflags/Libs 解析
   到 `/include`、`/lib`），配方复制并修复 `prefix=` 到真实 package_folder，保证
   meson 的 `dependency('gobject-2.0')`/`dependency('gio-2.0')` 正确解析。
4. **可选依赖关闭**：introspection/vapi（gobject-introspection）、gtk_doc（gi-docgen）、
   enable_vala（valac）在鸿蒙工具链缺失，配方一律 disable。
5. **共享库 codesign**：OHOS loader 校验 `.codesign` 段哈希，strip 会改写 .so 内容导致
   dlopen 报 Permission denied；`tc.strip=None`，且 `meson install` 清理 DT_RUNPATH
   后用 build 目录原始产物覆盖（E504，libsoup3 同款）。
6. **GObject 单副本（gsound 变体）**：ohpcd 只发布 static glib2。gsound 不链接
   libsoup3，没有 libsoup-3.0.so 的 GObject 导出表可借用（照搬 gssdp/gupnp 的
   .pc Libs 置空方案会报 g_object_ref 等 undefined symbol），因此**保留**静态
   glib2 链接列表直链进 libgsound.so，单副本性由消费进程不引入第二个 GObject
   共享库保证。

## 依赖

- glib2/2.88.0（glib/gobject/gio）
- libcanberra/0.30
