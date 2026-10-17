# libwnck3

libwnck is GNOME's Window Navigator Construction Kit for inspecting and controlling EWMH-compliant X11 desktops.

## 功能概述

- 枚举窗口、应用、工作区和屏幕
- 读取窗口状态、图标、资源占用及窗口管理器能力
- 提供任务列表、窗口选择器和工作区分页器 GTK 控件
- 发送标准 EWMH 窗口管理请求

## OHOS 适配

HarmonyOS PC 使用 GTK Broadway 显示控件。libwnck 的窗口管理数据面仍通过已发布的 X11 客户端库连接真实 X 服务器；适配层补足 Broadway GTK 不提供的 GDK-X11/Cairo-Xlib 胶水，并以 `XGetImage` 转换窗口图标 Pixmap，没有删除或伪造核心功能。

## 依赖关系

- glib/2.84.0.1
- gtk/3.24.43
- cairo/1.18.4
- libx11/6.4.0
- libxres/1.2.1
- libxi/6.1.0

## 参考资料

- https://gitlab.gnome.org/GNOME/libwnck
- https://download.gnome.org/sources/libwnck/43/
