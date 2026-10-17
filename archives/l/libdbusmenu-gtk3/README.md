# libdbusmenu-gtk3

A small library for passing menus over D-Bus (Canonical/Ayatana DBusMenu
specification): a pure-GLib menu model (libdbusmenu-glib, GDBus based) plus
GTK3 bindings (libdbusmenu-gtk3).

## 已编译版本

- 16.04.0 (built — MateBook 真机构建/上游测试/消费者测试/W4 审计全部通过)

## 依赖

- glib (gio/GDBus — client/server transport)
- gtk3 (dbusmenu-gtk bindings)
- json-glib (仅上游测试构建)

## OHOS 适配说明

- autotools 构建系统（2015 年代 config.guess/sub，见版本目录 patches/）
- 上游测试体系依赖 dbus-test-runner（未鸿蒙化）与 Xvfb（无 X server），
  适配策略与路径 B 测试报告见版本目录 notes.md
- D-Bus 会话总线由 dbus/1.14.10.x tool 包（dbus-run-session）在测试期提供，
  不进入库依赖图
