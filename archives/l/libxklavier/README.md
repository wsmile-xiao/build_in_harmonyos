# libxklavier

libxklavier 是一个基于 XKB 的键盘配置库，为 X11 键盘布局管理提供高层 API（查询/切换布局、监听键盘状态、读写 XKB 配置等），被 ayatana-indicator-keyboard 等桌面指示器所依赖。

## 功能概述

- `XklEngine`：键盘布局引擎（获取实例、监听键盘状态、锁定/切换布局组）
- `XklConfigRec`：键盘布局配置记录（从 X 服务器读取/写入）
- `XklConfigRegistry`：XKB 规则/模型/布局/选项注册表（解析 `/usr/share/X11/xkb/rules/*.xml`）
- ISO 3166/639 国家/语言代码名称解析（运行时数据，可选）

## OHOS 适配

- 构建系统：autotools（release tarball 自带 configure，无需 autoreconf）
- XKB 后端依赖 `libxkbfile`（提供 `XKBrules.h` 的 `XkbRF_*` 规则解析 API）。该依赖未发布到制品仓且系统未提供，**在 conanfile.py 内内嵌构建 libxkbfile（静态）并链接进 libxklavier.so**，保证配方自包含、CI 可复现。
- `libxi`（XInput）为可选依赖：configure 的 `PKG_CHECK_MODULES(XINPUT, ...)` 找不到时自动回退 `have_xinput=no`，XKB 后端仍可工作（仅失去设备发现特性），已裁剪。
- `gobject-introspection` / `vala` 为可选：`--disable-introspection` / `--disable-vala` 裁剪（纯库不需要 typelib/vapi）。
- `iso-codes` 为纯数据包（仅需 `iso-codes.pc` 元数据），配方内生成最小 `iso-codes.pc` 满足 configure；其数据文件仅运行时用于布局名称解析，缺失不影响功能。
- 需要 `gettext`（AM_GNU_GETTEXT external，msgfmt 工具）与 `libx11`、`glib`、`libxml2`（均已发布）。

## 依赖关系

| 依赖 | 版本 | 来源 |
|------|------|------|
| libx11 | 1.8.13 | conan 制品仓 |
| glib | 2.88.0.1 | conan 制品仓 |
| libxml2 | 2.15.3.1 | conan 制品仓 |
| gettext | 0.22.5.1 | conan 制品仓（tool_requires） |
| libxkbfile | 1.1.3 | 配方内内嵌构建（静态） |
| libxi | — | 可选，已裁剪 |
| iso-codes | — | 配方内生成最小 .pc |

## 参考资料

- 上游源码：https://gitlab.freedesktop.org/archived/libxklavier （已归档，镜像 https://github.com/linuxmint/libxklavier）
- 上游 tarball：https://deb.debian.org/debian/pool/main/libx/libxklavier/libxklavier_5.4.orig.tar.xz
