# libvirt-glib

## 简介

libvirt-glib 是 libvirt 的 GLib/GObject 封装库，为基于 GLib 的应用程序提供高层面向对象 API。

## OHOS 适配

**关键依赖**：
- libvirt >= 2.3.0（核心虚拟化库）
- glib-2.0 >= 2.48.0（GLib 核心）
- gobject-2.0 >= 2.48.0（GObject 类型系统）
- libxml-2.0 >= 2.9.1（XML 解析）

**三个子库**：
1. **libvirt-glib** - GLib 主循环集成和辅助 API
2. **libvirt-gconfig** - GObject 用于操作 libvirt XML 文档
3. **libvirt-gobject** - GObject 用于管理 libvirt 对象

**已知问题**：
- 版本 5.0.0 编译失败：libxml2 头文件路径问题
- meson 配置成功，但 ninja 编译阶段失败

## 依赖

- libvirt（虚拟化管理核心库）
- glib-2.0（GLib）
- libxml-2.0（XML 解析）
- gobject-introspection（可选，用于 GObject introspection）
- Vala（可选，用于 Vala bindings）

## 功能验证

```bash
# 检查编译产物
ls ~/usr/local/lib/libvirt-glib-*.so
pkg-config --modversion libvirt-glib-1.0
```

## 参考

- 官网：https://libvirt.org/glib/
- 源码：https://libvirt.org/sources/glib/
- Git：https://gitlab.com/libvirt/libvirt-glib