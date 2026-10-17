# dbus-glib

GLib/GObject 绑定层（legacy 高层 API），构建在 libdbus 之上：提供 DBusGConnection/DBusGProxy、
GValue 与 D-Bus 编解码互转、可特化 GType 系统（数组/字典/结构体）、错误映射，以及把 D-Bus
introspection XML 生成 GLib 桩代码的工具 `dbus-binding-tool`。

- 上游: https://dbus.freedesktop.org/dbus-glib/ （gitlab.freedesktop.org/dbus/dbus-glib）
- 许可: MIT / AFL-2.1（双许可，源码 SPDX 头）
- 依赖: glib、dbus（OHOS 制品仓均为静态包）

## 鸿蒙 PC 适配要点

1. **默认静态构建**：glib/2.88.0 OHOS 二进制只有静态库；shared 构建会把 glib 吞进
   libdbus-glib-1.so 形成第二份 GType 运行时（实测最终 unref 走 dispose 时 PC=0 崩溃）。
   配方 `shared` 默认 False，且 OHOS 上 glib 缺 `.so` 时请求 shared 会显式报错。
2. **E236**：依赖 `.la` 元数据不可迁移；配方经构建私有 la-free 目录喂 configure，并在
   package 阶段删除产物 `.la`。
3. **平台补丁**：config.guess/config.sub OHOS 三元组、configure umask（HMDFS）、
   测试 socket 可移植性（abstract AF_UNIX 优先）。
4. 设备无 D-Bus session bus 工具（dbus-daemon/dbus-run-session 不存在），3 个 bus 依赖
   测试无法运行，已在 test_package/MANIFEST.yml 记录原始错误；peer-to-peer IPC 与全部
   无总线测试真实通过。

版本详情见 `0.114/notes.md`。
