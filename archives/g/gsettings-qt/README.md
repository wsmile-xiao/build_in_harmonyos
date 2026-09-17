# gsettings-qt

`gsettings-qt` 提供 GSettings（GLib 的应用配置框架）的 Qt 绑定：`libgsettings-qt` 库
（Qt5 变体 `libgsettings-qt1`、Qt6 变体 `libgsettings-qt6`）与 QML 模块 `GSettings`
（API 版本 1.1）。应用可用 C++（`QGSettings`）或 QML 读写系统/应用配置。

本仓库归档在 **HarmonyOS PC（OHOS / aarch64）** 上以 **Qt6** 模式构建的官方发布版本。

- 上游仓库：https://gitlab.com/ubports/development/core/gsettings-qt
- 上游维护方：UBports / Debian UBports Team
- 许可证：LGPL-3.0-only
- 构建系统：CMake（本归档固定 `-DENABLE_QT6=ON`；上游默认 Qt5）

## 归档版本

| 版本 | 状态 | 构建日期 | 说明 |
|---|---|---|---|
| 1.1.1 | built | 2026-09-15 | Qt6 模式；libgsettings-qt6 + QML 模块 GSettings 1.1；上游 ctest 16 项全通过 |

## 产物（1.1.1）

| 路径 | 说明 |
|---|---|
| `lib/libgsettings-qt6.so.1.0.0`（+ `.so.1`、`.so`） | 库本体，SOVERSION 1 |
| `include/aarch64-linux-ohos/qt6/QGSettings/qgsettings.h`、`QGSettings` | 公开头文件与转发头（`#include <QGSettings>`） |
| `lib/pkgconfig/gsettings-qt6.pc` | pkg-config 元数据（`Requires: gio-2.0`） |
| `lib/qt6/qml/GSettings/` | QML 模块（`qmldir`、`libGSettingsQmlPlugin.so`、`plugins.qmltypes`） |

## 依赖

- 构建/运行：`qtbase/6.11.1`（Qt6Core）、`qtdeclarative/6.11.1`（Qt6Qml、Qt6QuickTest、`qmlplugindump`）、`glib/2.88.3`（gio-2.0）
- 构建工具：`pkgconf/3.0.6`（`find_package(PkgConfig)`）、`cmake-extras/1.9`（QmlPlugins 模块）

## 消费方式

```cmake
# CMake（pkg-config）
pkg_check_modules(GSETTINGSQT6 REQUIRED IMPORTED_TARGET gsettings-qt6)
target_link_libraries(app PRIVATE PkgConfig::GSETTINGSQT6)
```

```qmake
# qmake
PKGCONFIG += gsettings-qt6
```

```cpp
#include <QGSettings>
QGSettings settings("org.example.app");
settings.set(QStringLiteral("someKey"), 42);
```
