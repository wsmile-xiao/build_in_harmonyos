# glib2

GLib — GNOME 核心通用 C 工具库（glib / gobject / gio / gmodule / gthread）。
提供数据结构、对象系统 (GObject)、主循环、I/O (GIO)、线程、正则 (PCRE2) 等。

- 上游：https://gitlab.gnome.org/GNOME/glib
- 构建系统：meson (≥ 1.4) + ninja
- 许可证：LGPL-2.1-or-later

## 鸿蒙适配要点

1. **host_system 扩展**：OHOS conan profile 把 OHOS 自动映射为 meson `host_system='harmonyos'`。
   gio-launch-desktop 调用的 `_g_fd_is_journal` 仅在 `host_system=='linux'` 时编译
   （gjournal-private.c），harmonyos 下会链接失败；补丁把关键 linux 分支扩展到 harmonyos。
   鸿蒙内核兼容 Linux 接口，走 linux 分支是正确的。
2. **netlink 禁用**：鸿蒙不开放 netlink。`HAVE_NETLINK` 由 `<linux/netlink.h>` 头存在性决定
   （与 host_system 无关），显式在 harmonyos 上关闭，避开 netlink 网络监视器与
   sockaddr_storage 头冲突。
3. **pcre2 发现**：Conan 的 pcre2 包 pkg-config 名为 `pcre2`，glib 上游查找 `libpcre2-8`，
   补丁让 glib 两者都接受。
4. **可选依赖关闭**：libmount / selinux / nls(gettext) / introspection 在鸿蒙工具链缺失，
   配方中一律 disable。

## 依赖

- libffi/3.4.4（gobject 闭包）
- pcre2/10.45（glib 正则）
- zlib/1.3.1（GIO 压缩）
