# libcryptui

libcryptui 是 GNOME Seahorse（密码与密钥管理器）拆出的**密钥选择/加密 UI 库**：提供"选择收件人/签名密钥"的对话框（`CryptUIKeyChooser`）与可直接嵌入的密钥列表/下拉控件（`CryptUIKeyList`/`CryptUIKeyCombo`），以及基于 `GtkTreeModelSort` 的密钥模型（`CryptUIKeyStore`）。供第三方应用复用，无需自行实现 OpenPGP 密钥挑选 UI。

**官网**: https://gitlab.gnome.org/Archive/libcryptui

**分类**: library

**上游版本**: 3.12（本归档 **3.12.2**，上游末次发布，2014 年后停更）

## 版本列表

- 3.12.2 (2026-10-01) - built（库本体 + gsettings schema；依赖 gtk/3.24.43、dbus-glib/0.114.1）

## 依赖

- gtk (gtk+-3.0，传递 glib/gio/gobject/pango/cairo/gdk-pixbuf/atk)
- dbus-glib (dbus-glib-1；本图谱解析为静态归档，符号静态并入 `libcryptui.so`)
- expat （经 gtk 链与 dbus 链的传递依赖；见版本级 notes 的版本对齐说明）

## 编译说明

libcryptui 使用 autotools 构建系统。推荐配置：

```bash
conan create archives/l/libcryptui/3.12.2 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

上游 tarball 的 `SUBDIRS` 同时构建 `daemon/`（gnome-keyring + gpgme）与 `libegg/`（libSM/libICE），这两条支线与库本体无关却让依赖面失控——本归档在补丁中把 `SUBDIRS` 裁为 `libcryptui data`，并同步降级 configure 中对应的硬闸（intltool/XML::Parser、SM/ICE、glib-compile-schemas）。

库本体产品的 `cryptui-0.0.pc` 声明 `Requires: gtk+-3.0 gio-2.0 dbus-glib-1`，`Cflags: -I${includedir}/libcryptui`；消费者还可按需把 `share/glib-2.0/schemas` 并入 `GSETTINGS_SCHEMA_DIR` 以启用 settings 后端。
