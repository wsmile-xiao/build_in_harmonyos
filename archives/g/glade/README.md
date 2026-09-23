# glade — GNOME user interface designer

Glade 是 GNOME 的 GTK+ 用户界面设计器：可视化拖拽设计 GTK+ 3 界面并
保存为 `.glade` XML（GtkBuilder 格式）。附带 `libgladeui` 设计时库，
可供 IDE（如 Anjuta/GNOME Builder）集成。

- 上游: https://gitlab.gnome.org/GNOME/glade
- 许可: GPL-2.0-or-later
- 语言: C（meson 构建）

## OHOS PC 适配（3.40.0）

- 依赖：gtk/3.24.43（broadway 后端）、glib/2.84.0.1、libxml2/2.15.3
  （制品仓均已发布）
- 产物：`bin/glade`、`bin/glade-previewer`、`lib/libgladeui-2.so`、
  GTK+ 部件 catalog 与 adaptor 模块
- 上游测试：1390/1392 通过（add-child 1228、create-widgets 154、
  refcount 1、toplevel-order 7；modules 2 例需 python/gjs plugin，
  OHOS 上禁用——生态缺失非适配缺陷）。测试跑在 broadwayd 虚拟显示下。
- 适配细节见 [3.40.0/notes.md](3.40.0/notes.md)
