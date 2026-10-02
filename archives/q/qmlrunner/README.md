# qmlrunner

Runner for QML-only apps（Qt5 QML 应用启动器）。按约定加载
`PREFIX/appname/qml/appname.qml` 作为应用窗口，支持翻译
（`PREFIX/appname/translations/appname-LOCALE.qm`）、回退图标
（`PREFIX/appname/icons`）与附加 QML 导入路径（`-path`，可重复）。

- 上游: https://github.com/rinigus/qmlrunner
- 许可证: GPL-3.0-or-later
- 适配版本: 1.0.2

## 使用

```
qmlrunner [-P prefix] [-path qml_path]... [-scale|-noscale] appname [--] [app_options]
```

默认 prefix 为 `/usr/share`，即加载 `/usr/share/<appname>/qml/<appname>.qml`。

## OHOS PC (aarch64) 适配要点

- 构建系统 qmake(.pro) → CMake（qt5-qtbase/5.15.2.2 + qt5-qtdeclarative/5.15.2
  手动路径接线；main.cpp 无 Q_OBJECT，无需 moc）。
- 依赖: `qt5-qtbase/5.15.2.2`（Core/Gui/Widgets）、`qt5-qtdeclarative/5.15.2`
  （Qml/Quick）。
- 平台运行时: OHOS PC 当前由 qt5-qtbase 提供 offscreen/minimal/vnc 平台插件；
  headless 环境用 `QT_QPA_PLATFORM=offscreen` + `QT_QUICK_BACKEND=software`。
  运行时需要 `QT_PLUGIN_PATH=<qt5-qtbase>/plugins` 与
  `QML2_IMPORT_PATH=<qt5-qtdeclarative>/qml`。

## 验证

`test_package/test.sh`：offscreen QPA + 软件渲染下加载真实 QML 窗口应用
（正例 ×2），并以 4 个负例对照验证 CLI 契约与退出码（255/253/254/254）。
