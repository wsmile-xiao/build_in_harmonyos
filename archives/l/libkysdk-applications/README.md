# libkysdk-applications

openKylin 应用层 SDK（`kysdk`）——提供 openKylin/UKUI 桌面应用使用的 **kdk:: Qt 扩展控件集**
以及若干应用辅助库。下游的 UKUI 面板/小程序（如网络小程序 `kylin-nm-plugin`）通过
`using namespace kdk;` 使用其中的控件类。

## 功能概述

顶层 qmake 工程 `kysdk-application.pro` 由多个子模块组成，本制品仓归档的模块：

| 模块 | 产物 | 内容 |
|------|------|------|
| `kysdk-qtwidgets` | `libkysdk-qtwidgets.so` | kdk:: 控件集：`KSwitchButton`、`KBorderlessButton`、`KTabBar`、`KPasswordEdit`、`KDialog`、`KWidget`、`KListWidget`、`KAboutDialog` … |
| `kysdk-alm` | `libkysdk-alm.so` | 单实例应用辅助（`SingleApplication`） |
| `kysdk-ukenv` | `libkysdk-ukenv.so` | 系统环境接口（用户手册、货币） |
| `kysdk-widgetutils` | `libkysdk-widgetutils.so` | 窗口显示控制辅助 |

上游还有 `kysdk-waylandhelper` / `kysdk-kabase` / `kysdk-appconf2` 三个模块，在 HarmonyOS PC 上
因依赖链不可得而裁剪（见下）。

## OHOS 适配

制品仓中同一上游版本有 **两代 Qt 构建**，按消费者的 Qt 世代选择：

| 版本 | Qt | Conan 依赖 | 用途 |
|------|----|-----------|------|
| `3.0.1.2` | **Qt5** | `qt5-qtbase/5.15.2.2` | 既有 Qt5 消费者（保持不动） |
| `3.0.1.2.1` | **Qt6** | `qtbase-sql-dbus/6.11.1` | Qt6 消费者（例如 `kylin-nm-plugin/4.0.0.1`） |

**关键点**：`KSwitchButton : public QPushButton` 等控件派生自 Qt 控件类，因此 Qt5 与 Qt6 构建
**ABI 不兼容**；Qt6 消费者必须使用 `3.0.1.2.1`（并且 Qt5 构建的 `qt5-qtbase` 会把 `zlib/1.3.1`
拖进 Qt6 的 `zlib/1.3.2` 依赖图，无法在同一图内共存）。

两代构建共同的适配要点：

* 裁剪依赖 OHOS 不可得链的模块：`kysdk-waylandhelper`（wayland-client/server、xcb、KWaylandClient）、
  `kysdk-kabase`（systemd/kylog/kyconf）、`kysdk-appconf2`（kysdk-config/KSettings）。
* `kysdk-qtwidgets` 去掉 X11/xcb/KWindowEffects/gsettings-qt6/waylandhelper；`xatom-helper` 与
  SVG 渲染以最小实现 stub（对外 API 签名保留）。
* `QGSettings` 仅存于私有 `.cpp`——公共头用前向声明，避免与消费者自己的 gsettings-qt 头冲突。
* 安装布局：头文件平铺在 `include/kysdk/applications/`，**同时**通过 `include` 与
  `include/kysdk/applications` 两个 `-I` 暴露，使 `#include <kwidget.h>` 与
  `#include <kysdk/applications/kwidget.h>` 都能解析。
* 不执行 `make install`（上游 `target.path` 指向 Qt 安装前缀与 `/usr/include`）：由配方
  `package()` 从构建树 staging，产物完全可重定位，不写 `/usr`。
* 提供 pkg-config 模块 **`kysdk-applications`**（下游 `.pro` 的 `PKGCONFIG += kysdk-applications`），
  `Cflags: -I${includedir} -I${includedir}/kysdk/applications`，
  `Libs: -lkysdk-qtwidgets -lkysdk-alm -lkysdk-ukenv -lkysdk-widgetutils`。

## 依赖关系

* 编译/运行依赖：`qtbase-sql-dbus/6.11.1`（Qt6Core/Gui/Widgets/Network/DBus；`FEATURE_dbus=ON`）
  或 `qt5-qtbase/5.15.2.2`（Qt5 版本）。
* 不依赖 Qt6Svg / Qt6Sql（SVG 渲染与 QSql 分支已裁剪）。

## 参考资料

* 上游源码仓库：<https://gitee.com/openkylin/libkysdk-applications>
* 源码（3.0.1.2 orig.tar.xz）：<https://deb.debian.org/debian/pool/main/libk/libkysdk-applications/>
* 版本级适配笔记：`3.0.1.2.1/notes.md`、`3.0.1.2/notes.md`
