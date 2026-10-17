# libexif-gtk

## 简介

libexif-gtk 是 [libexif](https://libexif.github.io/) 项目的配套控件库：为 GTK 程序提供显示与编辑 EXIF 标签的 widget
（`GtkExifBrowser`、`GtkExifContentList`、`GtkExifEntry*` 系列，以及 `gtk-extensions/` 下的通用控件扩展）。

本仓归档的 **0.5.0** 为 **GTK3** 变体（上游默认构建 GTK2，本配方与 Debian 打包一致走 `--with-gtk3`），
产物为共享库 `libexif-gtk3.so.5.1.0` + `libexif-gtk3.pc`（另有同目录 `libexif-gtk3.a`）。

- 上游仓库：https://github.com/libexif/libexif-gtk
- 发布 tag：`v0.5.0`（commit `990b5ec933d9558a48562dc408c68d450736bd45`，2020-08-31）
- 许可证：LGPL-2.1-or-later

## OHOS 适配

- 源码取上游官方 GitHub release 资产 `libexif-gtk-0.5.0.tar.gz`（自带 `configure`/`Makefile.in`，无需 autoreconf）
- 平台三元组（E007/E072/E122）：`config.guess` 增 HarmonyOS 识别并输出标准三元组
  `aarch64-unknown-linux-ohos`；`config.sub` 的 basic system types 列表接受 `linux-ohos*`
- HMDFS 权限（E136）：`configure` 的临时目录改为 `${HOME}/tmp` + `umask 022`
  （原 `umask 077` 在 HMDFS 上生成不可写目录，`config.status` 报错）
- i18n：补齐上游 `#else`（非 NLS）分支遗漏的 `bind_textdomain_codeset` 桩，
  消除共享库未定义符号（OHOS 无 libc libintl，lld 默认拒绝带未定义符号的 shlib）
- 构建参数：`--with-gtk3 --disable-rpath --disable-nls`（NLS 关闭原因见 version 目录 notes.md）
- 上游无自动化测试；`tests/test-libexif-gtk` 为交互式示例，已用 GTK3 broadway 后端实测运行

## 依赖

- `libexif/0.6.26.1`（EXIF 数据模型，直接链接）
- `gtk/3.24.43`（GTK3 控件基座；`gdk-pixbuf` 经 `gtk+-3.0.pc` 的 Requires 提供）
- 构建期需要 `pkg-config`（`PKG_PROG_PKG_CONFIG`；由 CI profile 的 PATH 提供）

## 功能验证

```bash
# 消费端（Conan）
conan install --requires=libexif-gtk/0.5.0 ...
# test_package 6 断言全通过（含 1 条鸿蒙特有用例 OHOS-1）
```

## 版本

| 版本 | 状态 | 说明 |
|---|---|---|
| 0.5.0 | built | GTK3 变体；17 个补丁（平台识别/三元组 3（含 HMDFS 临时目录）+ 非 NLS i18n 桩 14） |
