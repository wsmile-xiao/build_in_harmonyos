# GOffice — 文档对象与工具库（Gnumeric 核心库）

## 简介
GOffice（libgoffice）是一个面向文档的对象/组件库，为 Gnumeric 等应用提供数字格式化、
图表、组件快照等文档中心化工具。goffice 是 GTK+3 GUI 库，头文件展开依赖 gtk/cairo/pango/gsf/glib。

## 功能
- 数字格式（go_format_* API）
- 组件与图表对象
- 文档中心化数据模型

## OHOS 适配
- GTK+ 栈（gtk+/pango/gdk-pixbuf/atk/harfbuzz/fribidi/libepoxy 等）由 cmd-pkgs 预编译包提供
- 底层库（cairo/pixman/libpng/freetype/fontconfig/zlib/expat/libgsf）由 ohpcd conan 制品仓提供
- librsvg 在 OHOS 不可用（无 Rust 工具链），通过补丁改为可选依赖 `--without-rsvg`
- intltool 需 XML::Parser（OHOS 缺失），通过 intltool-merge shim 禁用 NLS

## 依赖
- conan：cairo/1.18.4、pixman/0.46.4、libpng/1.6.58、freetype/2.14.3、fontconfig/2.18.1、
  zlib/1.3.1.1、expat/2.8.2、libgsf/1.14.58
- cmd-pkgs：gtk+/pango/gdk-pixbuf/atk/harfbuzz/fribidi/libepoxy/glib/libxml2 等

## 许可证
GPL-2.0-or-later

## 参考资料
- 上游仓库：https://gitlab.gnome.org/GNOME/goffice
- 源码下载：https://download.gnome.org/sources/goffice/0.10/
