# gupnp

GUPnP — 基于 GObject 的 UPnP 协议栈核心库，构建在 gssdp（SSDP 发现层）之上，
提供 `GUPnPContext`（内嵌 HTTP 服务器的网络上下文）、`GUPnPControlPoint`
（控制点）、`GUPnPRootDevice`（根设备）、`GUPnPServiceProxy`（服务代理）等
对象，用于 UPnP 设备/服务的发现、描述加载、动作调用与事件订阅。

- 上游：https://gitlab.gnome.org/GNOME/gupnp
- 构建系统：meson (>= 0.54.0) + ninja
- 许可证：LGPL-2.1-or-later

## 鸿蒙适配要点

1. **依赖栈**：直接依赖 glib2（glib/gobject/gio/gmodule/gio-unix）、
   libsoup3（libsoup-3.0）、gssdp（gssdp-1.6 >= 1.6.5）、libxml2
   （libxml-2.0）。zlib 经根级 override 钉在 PIC 变体 1.3.1.1。
2. **netlink 探测加固**（补丁 0001）：上游用单头 `cc.has_header` 探测
   `linux/rtnetlink.h`，在 OHOS sysroot 假阳性（单头可编译，但与
   `sys/socket.h` 同译单元即触发 `sockaddr_storage` 重定义）。补丁把探测改成
   与真实翻译单元一致的组合编译探测，失败即走上游 unix context manager
   （ifaddrs）路径——无平台宏、无功能删减。
3. **GObject 单副本**：ohpcd 只发布静态 glib2；GLib 系 .pc 的 Libs 全部剔除
   静态 glib，`libgupnp-1.6.so` 对 g_* 保持 UND，运行时统一解析到
   libsoup-3.0.so 导出的唯一 gobject 副本（gssdp 1.6.6 同款铁证方案）。
4. **最小补链归档**：gupnp 调用的 `g_uuid_string_random` 与
   `g_zlib_compressor_new` 是 libsoup-3.0.so 未导出的 glib/gio API；配方从
   glib2 静态库提取仅有的两个定义翻译单元（guuid.c.o、gzlibcompressor.c.o）
   组成 libglib-min.a 补链，避免整档级联（实测整档会拉入 3812 个符号）。
5. **glib2 .pc 前缀修复**：glib2 包 .pc 以 `prefix=/` 安装，且包内 libffi.pc
   前缀损坏（`-L//lib -lffi` 设备不可解析）；配方生成 pc-fix 复制件（修
   prefix、Libs 置空、Requires 剔除 libffi）并前置到 PKG_CONFIG_PATH。
6. **gnome.mkenums()**：`libgupnp/meson.build` 用 `gnome.mkenums()` 生成枚举
   代码，meson 经 pkg-config 变量 `glib_mkenums` 定位工具；配方向生成的
   glib-2.0.pc 追加该变量并把 glib2 包 bin 工具钉进 meson 原生 [binaries]。
7. **禁 strip + RUNPATH 覆盖回滚**：共享库 strip 会破坏 .codesign 内嵌哈希
   （dlopen Permission denied）；meson install 清理 DT_RUNPATH 会改写 .so，
   用 build 目录原始链接产物覆盖安装产物。
8. **命令行工具**：`gupnp-binding-tool-1.6` 为上游自带纯 Python 3 脚本（设备
   `python3` 可运行），见 commands.json。

## 测试

上游测试 `meson test`（OHOS 设备原生执行）：7 个测试程序、56 个 TAP 子用例，
56/56 通过、0 失败、0 跳过（context 22、service-proxy 13、bugs 10、
context-filter 4、context-manager 3、service 2、acl 2）。
