# libadwaita

GNOME Adwaita 主题控件库（GTK4 生态的 Adwaita 风格 widget 库），Meson 构建。

## 版本

| 版本 | 构建系统 | 状态 | 说明 |
|------|----------|------|------|
| 1.2.0 | meson | built | OHOS PC (aarch64) 适配：跟随 gtk4 的 Broadway-only 后端约束，禁用 introspection/vapi/gtk_doc/examples，保留上游 37 个测试程序 |

## 上游信息

- 官方仓库：https://gitlab.gnome.org/GNOME/libadwaita
- 官方 tag 归档：https://gitlab.gnome.org/GNOME/libadwaita/-/archive/1.2.0/libadwaita-1.2.0.tar.gz
- 许可：LGPL-2.1-or-later

## OHOS 适配要点

- 依赖：gtk4/4.22.4、glib/2.84.0.1.1 (shared=True)、fribidi/1.0.16（zlib/fontconfig override 对齐 gtk4 图）
- glib bin 工具（glib-compile-resources 等）需按 ML-0043 重签名才能在 OHOS 执行
- PkgConfigDeps 生成的 .pc 需补 glib 工具变量与 fribidi 子目录 include
- 库产物：libadwaita-1.so，头文件 include/libadwaita-1，pkg-config 名 libadwaita-1
- 详细适配过程见 1.2.0/notes.md
