# libcanberra-gtk3 0.30 适配笔记

## 概述

libcanberra-gtk3 是 XDG Sound Theme/Name 事件声音库（libcanberra）的
GTK3 绑定。上游 `-version-info 1:9:1` → soname `libcanberra-gtk3.so.0`
（真实文件 `libcanberra-gtk3.so.0.1.9`）。本包只交付 GTK3 产物：
`libcanberra-gtk3.so.1`、GTK3 模块 `libcanberra-gtk3-module.so`、
公共头 `canberra-gtk.h` 与 `libcanberra-gtk3.pc`；核心
`libcanberra.so` 由 `libcanberra/0.30` 提供。

## OHOS 适配要点

- **Broadway 兼容（关键）**：上游 `configure.ac` 的 GTK3 探测
  `PKG_CHECK_MODULES(GTK3, [ gtk+-3.0 gthread-2.0 glib-2.0 >= 2.32 gdk-3.0 x11 ])`
  **硬依赖 X11 与独立的 gdk-3.0 模块**；`src/canberra-gtk.c` /
  `src/canberra-gtk-module.c` 又无条件 `#include <gdk/gdkx.h>` /
  `<X11/Xatom.h>` 并调用 `XGetWindowProperty` / `GDK_WINDOW_ID` /
  `XInternAtom`。ohpcd 发布的 `gtk/3.24.43` 是纯 broadway 后端
  （`gdkconfig.h` 中 `GDK_WINDOWING_X11` 未定义），且只发布单一
  `gtk+-3.0` pc 模块（无独立 `gdk-3.0`），库存 configure 直接中止、
  源码也无法编译。`patches/0007` 做三件事：
  - 从 `configure.ac` 与生成的 `configure` 的 GTK3 pkg-config 探测里
    去掉 `gdk-3.0 x11`（`configure` 中该字符串出现 8 处）；
  - 把所有 X11 头文件包含与 X11 专属代码路径（`window_get_desktop` /
    `display_get_desktop` / `window_is_xembed` 三个辅助函数，以及
    `ca_gtk_proplist_set_for_screen` / `ca_gtk_proplist_set_for_widget` /
    `dispatch_sound_event` 里的 X11 属性设置）用
    `#ifdef GDK_WINDOWING_X11 ... #endif` 包起来；
  - 修正 `libcanberra-gtk3.pc.in`：去掉 `-lX11`，`Requires` 改用已发布
    的核心 pc 名（`Requires: canberra gtk+-3.0`），`Libs` 补
    `-lcanberra`，保证 pkg-config 消费者经 `libcanberra/0.30` 解析核心库。
- **只构建 GTK3 目标**：`src/Makefile.am` 的 `libcanberra-gtk3.la` 与
  `libcanberra-gtk3-module.la` 链接 build-tree 的 `libcanberra.la`。配方
  用 `make -C src libcanberra.la libcanberra-gtk3.la libcanberra-gtk3-module.la`
  构建（核心库仅作链接期依赖），`package()` 只手工复制 GTK3 产物，
  不复制核心库/二进制/`.la`，与 `libportal-gtk3` 的"跨账号同链分工"
  模式一致（R26 同名库隔离）。
- **configure 模式**：沿用 `libcanberra/0.30` 的 CI 验证模式——configure
  在 `/system/bin/sh` 下以 `--host=aarch64-linux-ohos --srcdir=...` 运行，
  只给 `--host` 不给 `--build`；`config.guess`/`config.sub` 由
  `patches/0004`/`0005` 识别 HarmonyOS；生成的 configure 里 `umask 077`
  （全文恰好两处）改写为 `umask 022`。
- **vorbis 强制依赖绕过**：与核心包一致，`VORBIS_CFLAGS=-DHAVE_VORBIS=0`
  与 `VORBIS_LIBS=' '` 同时非空走 pkg.m4 env 分支，`patches/0001`/
  `0002` 把 Ogg Vorbis 解码路径包进 `#if HAVE_VORBIS`。
- **驱动选择 `--with-builtin=null`**：pulse/alsa/gstreamer 驱动是 libltdl
  可加载模块，OHOS 不适用；`--with-builtin=null` 把 null.c 编进核心库并
  关闭 BUILTIN_DSO，不链 `$(LIBLTDL)`（`patches/0006` 中和 configure 的
  硬 libltdl 门禁）。
- **导出面**：`canberra-gtk.h` 的 7 个公共函数
  （`ca_gtk_context_get`（`#ifndef GDK_MULTIHEAD_SAFE`）、
  `ca_gtk_context_get_for_screen`、`ca_gtk_proplist_set_for_widget`、
  `ca_gtk_play_for_widget`、`ca_gtk_proplist_set_for_event`、
  `ca_gtk_play_for_event`、`ca_gtk_widget_disable_sounds`）。

## 测试

test_package 构建一个 executable（链接
`libcanberra-gtk3::libcanberra-gtk3`，`-Werror`）：

1. `libcanberra_gtk3_api_surface` — 对 `canberra-gtk.h` 全部导出符号各取
   强类型函数指针（载入期活重定位）；若 `gtk_init_check(NULL, NULL)` 成功
   （目标有可用 display），再驱动 `ca_gtk_context_get_for_screen` 与
   `ca_gtk_proplist_set_for_widget` / `ca_gtk_widget_disable_sounds`；
   无头环境下跳过 GTK 运行时检查，符号重定位检查仍作为门禁。

> 上游 libcanberra 0.30 **没有自动化测试**：无 check_PROGRAMS/TESTS；唯一可执行
> test-canberra 是 noinst 演示程序（无断言，需真实音频后端播放系统声音文件）。
> 该 consumer 测试即"上游无测试、适配后补全"的覆盖（详见 PR body）。
---

**编译结束**: 2026-09-26 15:29
**最终状态**: built
