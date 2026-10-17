# libgoa

GNOME Online Accounts (GOA) 的客户端库：为桌面应用提供统一的「在线账号」访问面
（枚举账号、读取 OAuth2 / 密码 / Kerberos 凭据），运行时通过 D-Bus 与
goa-daemon 通信。

- 上游仓库: https://gitlab.gnome.org/GNOME/gnome-online-accounts
- 构建系统: Meson
- 依赖: glib/2.88.3（gio-2.0 / glib-2.0）
- 许可证: LGPL-2.1-or-later
- 产物: libgoa-1.0.so（SONAME libgoa-1.0.so.0）+ goa-1.0.pc

## 版本

- 3.58.1 — 当前适配版本（客户端库子集）
