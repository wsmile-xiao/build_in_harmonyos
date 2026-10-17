# libportal-gtk3

[![version](https://img.shields.io/badge/version-0.10.0-blue)](archives/libportal-gtk3/0.10.0)
[![status](https://img.shields.io/badge/status-built-green)](archives/libportal-gtk3/0.10.0)
[![license](https://img.shields.io/badge/license-LGPL--3.0--only-blue)](https://github.com/flatpak/libportal/blob/0.10.0/COPYING)

GTK3 backend of libportal — XDG desktop portal integration for GTK3 applications.

## 上游

- 仓库：https://github.com/flatpak/libportal（tag 0.10.0）
- 同一源码仓库通过 meson feature 选项产出多后端；本包只构建
  `backend-gtk3=enabled`（libportal-gtk3.so + portal-gtk3.h +
  libportal-gtk3.pc）

## 适配说明

- 构建系统 meson；OHOS aarch64（clang 15，musl libc）零补丁
- gtk 采用 ohpcd 已发布的 broadway 后端 gtk/3.24.43：gdkconfig.h 中
  GDK_WINDOWING_X11/WAYLAND 均未定义，上游 X11/Wayland 代码被条件编译
  剔除，`xdp_parent_new_gtk()` 的纯 GObject 路径天然兼容
- 运行时 NEEDED libportal.so.1，由 libportal/0.10.0 主件包提供（平台
  任务 #13396，跨账号同链分工）
- 上游 81 个 pytest 用例（dbus+dbusmock 框架）全量豁免：OHOS 无 D-Bus
  session bus（无 machine-id），详见版本目录 notes.md

## 依赖

| 依赖 | 版本 | 状态 |
|------|------|------|
| gtk | 3.24.43 | 已发布（broadway 后端） |
| libportal | 0.10.0 | 主件在途（#13396） |

## 使用

```bash
conan install --requires=libportal-gtk3/0.10.0
```

```c
#include <libportal-gtk3/portal-gtk3.h>

XdpParent *parent = xdp_parent_new_gtk(GTK_WINDOW(window));
```
