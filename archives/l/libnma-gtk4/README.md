# libnma-gtk4

## 简介

libnma-gtk4 是 libnma（NetworkManager UI utilities）的 GTK4 变体——
WiFi 对话框、EAP/无线安全编辑器、移动宽带向导等 NetworkManager
客户端 UI 组件的 GTK4 版本（`libnma-gtk4.so`）。

上游：https://gitlab.gnome.org/GNOME/libnma（同一源码树，meson 选项
`libnma_gtk4` 控制产出；gtk3 主库由姊妹包 libnma 交付）。

## OHOS 适配

- **构建系统**: meson（官方 release tarball，自带预转换 Gtk4 .ui 文件）
- **依赖**: gtk4/4.22.4（broadway 后端）、libnm/1.52.1、glib/2.84.0.1.1
- **补丁**: meson 新增 libnma_gtk3 选项——false 时只构建 gtk4 变体，
  共享源码用 gtk4 头编译（上游源码 gtk3/gtk4 双兼容）
- **gcr/iso-codes/mobile-broadband**: 关闭（ohpcd 未发布 gcr-4/gck-2；
  后两者仅影响数据目录宏）

## 依赖

- gtk4 4.22.4
- libnm 1.52.1
- glib 2.84.0.1.1
