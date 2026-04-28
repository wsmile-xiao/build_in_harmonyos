# glib

## 简介
GLib — GNOME 核心工具库，提供数据结构（GList, GHashTable, GArray）、事件循环（GMainLoop）、IO 抽象（GIO）、类型系统（GObject）等基础功能。许多 GNOME/GTK 应用和库的底层依赖。

## OHOS 适配
- Meson 在 HarmonyOS 上检测 `host_system` 为 `'harmonyos'` 而非 `'linux'`
- 需将所有 `host_system == 'linux'` 改为 `host_system in ['linux', 'harmonyos']`
- OHOS 内核头文件 `linux/socket.h` 与 musl `sys/socket.h` 有 `struct sockaddr_storage` 冲突，需用 `#define` 宏重命名
- 推荐使用 `default_library=static` 构建静态库，避免共享库运行时加载签名问题
- 需禁用：nls, libmount, selinux, tests, xattr, dtrace, systemtap, introspection, oss_fuzz

## 依赖
- 编译依赖：libffi, zlib, pcre2
- 运行依赖：无

## 功能验证
```bash
pkg-config --modversion glib-2.0
glib-compile-resources --version
```

## 参考
- 官方文档：https://docs.gtk.org/glib/
- 下载：https://download.gnome.org/sources/glib/
