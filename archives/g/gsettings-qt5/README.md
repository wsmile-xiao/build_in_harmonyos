# gsettings-qt5

`gsettings-qt` 提供 GSettings（GLib 的应用配置框架）的 Qt 绑定：`libgsettings-qt` 库
（Qt5 变体 `libgsettings-qt`、Qt6 变体 `libgsettings-qt6`）与 QML 模块 `GSettings`
（API 版本 1.1）。应用可用 C++（`QGSettings`）或 QML 读写系统/应用配置。

本归档目录存放上游 **Qt5** 模式构建（上游默认分支）的发布版本。同仓库另有
`archives/g/gsettings-qt/`，存放同一上游的 **Qt6** 模式构建；两者源 tarball 相同，
仅 Qt 主版本不同，用于满足不同 Qt 版本的下游消费者。

- 上游仓库：https://gitlab.com/ubports/development/core/gsettings-qt
- 上游维护方：UBports / Debian UBports Team
- 许可证：LGPL-3.0-only
- 构建系统：CMake（本归档 `-DENABLE_QT6=OFF`，即上游默认的 Qt5 分支）

## 为什么需要独立的 Qt5 包

Qt6 构建的 `libgsettings-qt6.so` 与 Qt5 程序 ABI 不兼容（QObject/QVariant/信号槽
体系不同），无法被 Qt5 消费者链接。Qt5 应用（例如 kylin-calendar）需要
`pkg_check_modules(... gsettings-qt)` + `#include <QGSettings>` + `-lgsettings-qt`，
因此需要本 Qt5 变体包（库名与 `.pc` 名在 Qt5 下不带版本后缀）。

## 归档版本

| 版本 | 状态 | 构建日期 | 说明 |
|---|---|---|---|
| 1.1.1 | built | 2026-10-08 | Qt5 模式；libgsettings-qt + QML 模块 GSettings 1.1；上游 ctest 16/16 断言通过 |

## 产物（1.1.1）

| 文件 | 说明 |
|---|---|
| `lib/libgsettings-qt.so.1.0.0`（+ `.so.1`、`.so`） | 库本体（SOVERSION 1，`DT_SONAME=libgsettings-qt.so.1`） |
| `include/aarch64-linux-ohos/qt5/QGSettings/{qgsettings.h,QGSettings}` | 公开头文件与转发头（消费方 `#include <QGSettings>`） |
| `lib/pkgconfig/gsettings-qt.pc` | pkg-config 元数据（`Requires: gio-2.0`） |
| `lib/qt5/qml/GSettings/{qmldir,libGSettingsQmlPlugin.so}` | QML 模块 GSettings 1.1 |

## 消费方式

```cmake
# pkg-config 路径（下游 kylin-calendar 用法）
pkg_check_modules(GSETTING REQUIRED gsettings-qt)
target_include_directories(app PRIVATE ${GSETTING_INCLUDE_DIRS})
target_link_libraries(app PRIVATE ${GSETTING_LIBRARIES})   # 另需自行提供 Qt5::Core
```

```cpp
#include <QGSettings>
QGSettings settings("org.kylin.calendar.plugin");
QGSettings::isSchemaInstalled("org.kylin.calendar.plugin");
settings.get("someKey");
```

## 详细说明

- 适配笔记（依赖结论、上游测试三步法、适配要点）：[`1.1.1/notes.md`](1.1.1/notes.md)
- 版本元数据：[`1.1.1/manifest.yaml`](1.1.1/manifest.yaml)
- 上游测试日志：[`1.1.1/reports/upstream-tests.log`](1.1.1/reports/upstream-tests.log)
