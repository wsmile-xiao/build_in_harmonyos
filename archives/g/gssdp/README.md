# gssdp

GSSDP — 基于 GObject 的 SSDP（简单服务发现协议）库，是 GUPnP 协议栈的底层依赖。
提供 `GSSDPClient`（发现客户端）、`GSSDPResourceBrowser`（资源浏览器）与
`GSSDPResourceGroup`（资源发布组）等对象，用于 UPnP/SSDP 设备发现与宣告。

- 上游：https://gitlab.gnome.org/GNOME/gssdp
- 构建系统：meson (>= 0.54.0) + ninja
- 许可证：LGPL-2.1-or-later

## 鸿蒙适配要点

1. **依赖栈**：直接依赖 glib2（glib-2.0 / gobject-2.0 / gio-2.0）与 libsoup3
   （libsoup-3.0）。注意 gssdp 本身不直接依赖 libxml2（那是 gupnp 的依赖）。
2. **gnome 模块交叉编译**：`libgssdp/meson.build` 用 `gnome.mkenums()` 生成枚举代码，
   依赖 glib2 包 `bin/glib-mkenums`（python 脚本）。配方 `generate()` 将其钉入
   meson 原生 `[binaries]` 段（`tc.binaries`），避免 pkg-config 变量回退失败。
3. **glib2 .pc 前缀修复**：glib2 包的 `.pc` 文件以 `prefix=/` 安装（Cflags/Libs 解析
   到 `/include`、`/lib`），配方复制并修复 `prefix=` 到真实 package_folder，保证
   meson 的 `dependency('gobject-2.0')`/`dependency('gio-2.0')` 正确解析。
4. **可选依赖关闭**：sniffer（gtk4）、introspection/vapi（gobject-introspection）、
   gtk_doc（gi-docgen）、manpages（pandoc）、examples 在鸿蒙工具链缺失，配方一律 disable。
5. **共享库 codesign**：OHOS loader 校验 `.codesign` 段哈希，strip 会改写 .so 内容导致
   dlopen 报 Permission denied；`tc.strip=None`，且 `meson install` 清理 DT_RUNPATH
   后用 build 目录原始产物覆盖（libsoup3 同款）。

## 依赖

- glib2/2.88.0（glib/gobject/gio/gmodule/gthread）
- libsoup3/3.6.5-r1（libsoup-3.0）
