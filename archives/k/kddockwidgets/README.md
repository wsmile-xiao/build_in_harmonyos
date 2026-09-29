# kddockwidgets

KDAB 的 Qt 停靠窗口框架（docking framework）。提供 QMainWindow 风格的停靠/浮动/标签页布局系统（dock widgets、drop area、layout save/restore），支持 Qt5 与 Qt6，含 qtwidgets 与 qtquick 两个前端。

- 上游仓库：https://github.com/KDAB/KDDockWidgets
- 许可证：GPL-2.0-only OR GPL-3.0-only
- 构建系统：CMake（≥3.15）
- OHOS 适配策略：Qt5 栈 + qtwidgets 前端（`KDDockWidgets_QT6=OFF`、`KDDockWidgets_FRONTENDS=qtwidgets`），上游自 v2.3.0 起默认 Qt6，Qt5 为受支持配置（`QT_MIN_VERSION 5.15`）
