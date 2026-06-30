# GTK4

GTK 4（GIMP Toolkit 4）是开源跨平台GUI工具包，为 GNOME 桌面环境提供核心图形界面支持。

## Available Version
- 4.22.4 (2026-05-30): Broadway backend for OpenHarmony

## Description
GTK 4 是用于创建图形用户界面的多平台工具包的最新主要版本，相比 GTK 3 提供了改进的渲染架构、事件处理和布局系统。

## Dependencies
- glib (2.88.0)
- pango
- cairo
- harfbuzz (需启用 glib 集成)
- gdk-pixbuf
- graphene
- fribidi
- libepoxy (1.5.10)

## Features (4.22.4)
- Broadway backend（HTML5/WebSocket远程渲染）
- 文件打印后端
- 无X11/Wayland/Vulkan支持（OHOS限制）
- 无GStreamer媒体后端
- 无introspection支持

## Usage
GTK 4 在 OHOS 上通过 Broadway backend 提供远程渲染能力：
```bash
# 启动 Broadway 服务
gtk4-broadwayd :0
# 通过浏览器访问 http://localhost:8080
# 运行 GTK 应用
GDK_BACKEND=broadway ./your-gtk-app
```

## Notes
- 在 OHOS 上仅支持 Broadway backend（无 X11/Wayland 显示）
- harfbuzz 必须启用 glib 集成才能编译 GTK4（hb-glib.h依赖）
- libepoxy 需手动创建 .so 符号链接（HMDFS不支持 ln -sf 覆盖）
- gdkdmabuf.c 中的 epoxy/egl.h include 需 HAVE_EGL 守卫（OHOS不提供EGL）