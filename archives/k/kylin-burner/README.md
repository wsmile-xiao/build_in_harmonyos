# 麒麟刻录 (kylin-burner)

麒麟刻录（kylin-burner）是 openKylin 麒麟桌面维护的光盘刻录与拷贝应用，由 GNOME Brasero 分叉而来。它构建三个共享库（libburner-media3、libburner-burn3、libburner-utils3）与 `burner` 主程序（GTK3 GUI，含 `--cli` 命令行烧录模式），支持 CD/DVD 数据盘、音频盘与映像文件的刻录、拷贝和校验。

## OHOS Adaptation

在 HarmonyOS PC 上，以下 GNOME/X11 组件不可用，已通过 pc 重定向 + 桩头（stub）方式适配：

- **gdk-x11-3.0**（GTK3 X11 后端；conan gtk3 仅构建 broadway 后端）— `gdk-x11-3.0.pc` 重定向（Requires: gtk+-3.0）+ `ohos-stubs/gdk/gdkx.h` 桩头；不定义 `GDK_WINDOWING_X11`，使 burner-app.c 的 X11 代码编译期排除
- **libcanberra-gtk3**（GTK3 音效后端；conan libcanberra 以 `--disable-gtk3` 构建）— `libcanberra-gtk3.pc` 重定向（Requires: canberra gtk+-3.0）+ `canberra-gtk.h` 桩头（`ca_gtk_play_for_widget` 返回 0，音效静默跳过）
- **intltool / XML::Parser**（翻译标记处理）— m4 shim（`IT_PROG_INTLTOOL`）指向 `intltool-merge-shim`（perl -pe 剥 `_` 翻译标记），.desktop/.xml 数据文件仍可生成
- **gnome-common / yelp-tools / gtk-doc**（GNOME 构建宏）— `m4/ohos-stubs.m4` 提供空宏 shim；NLS/po、docs、help 从构建中移除
- **外部刻录后端**（cdrtools / cdrdao / cdrkit / growisofs / libburnia）— 制品仓无对应包，configure 显式 `--disable-cdrtools --disable-cdrdao --disable-cdrkit --disable-growisofs --disable-search --disable-playlist` 等关闭，对应插件未构建
- **X11 会话管理 sm/ice** — configure 的 `BURNER_SM` 为硬性检查，以 libsm/1.2.6 + libice/1.1.2 conan 包补齐

应用可编译、可安装；GTK3 GUI 需要桌面会话（X11/GTK3 运行时），无显示环境下以 launcher 包装脚本（`bin/burner`）应答 `--version`/`--help`，真实 ELF 为 `bin/burner-bin`（不可执行）。完整烧录功能依赖外部刻录后端，后者在 HarmonyOS 生态中尚未发布；当前以平台可移植性验证为主。

## Build System

- **构建系统**：Autotools（上游 tarball 无 configure，需 `autoreconf -fi` 引导）
- **依赖**：glib/2.84.0.1、gtk/3.24.43、gstreamer/1.28.3、gst-plugins-base/1.28.3、libcanberra/0.30、libnotify/0.8.3、libxml2/2.15.3、libsm/1.2.6、libice/1.1.2、zlib/1.3.1.1（force，解决 glib/glib2 依赖图冲突）
- **源码**：[openKylin kylin-burner releases](https://gitee.com/openkylin/kylin-burner/releases)
- **主页**：<https://gitee.com/openkylin/kylin-burner>

## Version

- 3.0.11（built，2026-09-22）
