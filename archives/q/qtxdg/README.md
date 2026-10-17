# qtxdg (libqtxdg / Qt5Xdg)

`libqtxdg` 是 LXQt 维护的 **freedesktop.org XDG 规范**的 Qt5 实现。它向上提供
`Qt5Xdg`、`Qt5XdgIconLoader` 两个库与 Qt 图标引擎插件 `Qt5XdgIconPlugin`，
并被 kylin-calendar/5.0.0.0 通过 `find_package(Qt5Xdg 3.3.1 REQUIRED)` 使用。

- 上游仓库：<https://github.com/lxqt/libqtxdg>
- 上游版本：3.12.0（3.x 为 Qt5 版；4.x 才是 Qt6）
- 构建系统：CMake
- 许可证：LGPL-2.1-or-later

## 版本信息

| 版本 | 状态 | 说明 |
|------|------|------|
| 3.12.0 | built | 首次适配（Qt5，`>= 3.3.1` 满足 cal 需求） |

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| qt5-qtbase | 5.15.2.2 | Qt5 Core/Gui/Widgets/Xml/DBus |
| qt5-qtsvgv | 5.15.2.2 | Qt5Svg（要求 qt5-qtbase/5.15.2.2） |
| glib | 2.88.0 | XdgMimeApps 的 GLib 后端 |
| lxqt-build-tools | 0.13.0 | **未发布到制品仓**，配方自带官方源码构建（见 notes.md） |

## 产物

- `lib/libQt5Xdg.a`、`lib/libQt5XdgIconLoader.a`（**静态**，因 OpenHarmony 的 zlib/glib 仅非 PIC 静态库）
- `plugins/iconengines/libQt5XdgIconPlugin.so`（PIC 模块）
- `include/qt5xdg/`、`include/qt5xdgiconloader/`
- `share/cmake/qt5xdg{iconloader}/`、`lib/pkgconfig/`
- 无命令行可执行文件（`BUILD_DEV_UTILS=OFF`），故不需要 `commands.json`
