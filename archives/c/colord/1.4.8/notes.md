# colord 1.4.8 — OHOS 适配笔记

## 软件信息

- **名称**: colord
- **版本**: 1.4.8
- **上游**: https://github.com/hughsie/colord
- **构建系统**: Meson
- **许可**: LGPL-2.1+
- **语言**: C

## 依赖分析

### 制品仓已发布（✅）
- glib2/2.88.0 — GLib 核心库（gio, glib, gmodule, gio-unix）
- lcms2/2.19 — Little CMS 2 颜色管理库
- sqlite3/3.53.4 — SQLite 数据库（colord 用其存储配置数据）
- meson/1.11.0 — 构建工具

### 制品仓未发布（❌）— 通过禁用选项绕过
- libgusb — ColorHug 色度计 USB 库依赖。通过跳过 colorhug 子目录绕过
- libgudev — GObject udev 封装。通过使依赖可选 + 从 libcolord 依赖列表移除绕过
- libudev — udev 库。通过使依赖可选 + 在 cd-edid.c 中 __OHOS__ 守卫绕过

### 完整依赖链（meson.build 原始）
```
gio-2.0 >= 2.45.8  (glib2)
glib-2.0 >= 2.58   (glib2)
gmodule-2.0        (glib2)
gio-unix-2.0 >= 2.45.8  (glib2)
lcms2 >= 2.6       (lcms2)
sqlite3            (sqlite3)
gusb >= 0.2.7      (libgusb) -- 未发布，跳过 colorhug
gudev-1.0         (libgudev) -- 未发布，从 libcolord 移除
libudev            (libudev)  -- 未发布，__OHOS__ 守卫
```

## 适配方案

### 1. 禁用可选功能（meson project options）
禁用了以下 meson options 以消除不可用依赖：
- `daemon=false` — 守护进程需要 polkit, libudev, libsystemd
- `systemd=false` — OHOS 无 systemd
- `udev_rules=false` — OHOS 无 udev
- `introspection=false` — 需要 g-ir-scanner
- `man=false` — 需要 xsltproc
- `docs=false` — 需要 gtk-doc
- `bash_completion=false` — 需要 bash-completion
- `vapi=false` — 需要 vala 编译器
- `sane=false` — 需要 SANE 后端
- `session_example=false` — 需要 gnome-desktop
- `print_profiles=false` — 需要 argyllcms
- `argyllcms_sensor=false` — 需要 argyllcms
- `libcolordcompat=false` — 可选兼容库
- `tests=false` — 测试需要运行环境
- `installed_tests=false`

### 2. 补丁 0001-ohos-disable-udev-gudev-deps.patch
- 将 `gusb`, `gudev`, `libudev` 设为 `required: false`（原为 required）
- 从 `lib/colord/meson.build` 的 `colordprivate` 和 `colord` shared_library 依赖列表中移除 `gudev` 和 `libudev`
- 在 `lib/colord/cd-edid.c` 中用 `#ifndef __OHOS__` 守卫 `#include <libudev.h>` 和 hwdb 查找逻辑
- 跳过 `lib/colorhug` 子目录（依赖 gusb）
- 跳过 `po` 子目录（依赖 gettext i18n）
- 跳过 `meson_post_install.sh`（需要 chown）

### 3. pkg-config 兼容层
glib2 Conan 包只生成聚合的 `glib-2.0.pc`，而 meson 的 `dependency()` 按单模块名查找。
在 `generate()` 中补写 `gobject-2.0.pc`, `gio-2.0.pc`, `gio-unix-2.0.pc`, `gmodule-2.0.pc` 作为薄包装。

## 构建产物
- `lib/libcolord.so` / `lib/libcolordprivate.so`（动态）或 `.a`（静态）
- `bin/colormgr` — 颜色管理命令行工具
- `bin/cd-iccdump` — ICC profile dump 工具
- `bin/cd-fix-profile` — ICC profile 修复工具
- `bin/cd-it8` — IT8 工具
- `bin/cd-create-profile` — 创建 ICC profile 工具
- `include/colord-1/` — 头文件

## 验证
- conan create + test_package 全绿
- test_package 验证 CdColorRGB 和 CdIcc API 可用
