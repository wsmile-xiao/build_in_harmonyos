# qt5-qtquickcontrols2

Qt Quick Controls 2 — Qt 5.15.2 官方控件库模块。

## 内容
- **C++ 库**：`libQt5QuickTemplates2.so`（模板控件基类）、`libQt5QuickControls2.so`（QQuickStyle 等公共 API）
- **QML 模块**（qml/ 目录）：
  - `QtQuick/Controls.2` — 主模块 + Default 风格
  - `QtQuick/Controls.2/{Fusion,Imagine,Material,Universal}` — 四种内置风格
  - `QtQuick/Templates.2`、`Qt/labs/calendar`、`Qt/labs/platform`
- 公共头：`include/QtQuickControls2`（QQuickStyle）、`include/QtQuickTemplates2`

## 依赖
- qt5-qtbase/5.15.2.2（Core/Gui/Widgets + qmake 工具）
- qt5-qtdeclarative/5.15.2（Qml/Quick/QmlModels + 私有头）

## 消费者接入
```cmake
find_package(Qt5QuickControls2 CONFIG REQUIRED)
target_link_libraries(app PRIVATE Qt5::QuickControls2)
```
运行期 QML 导入路径需包含本包 `qml/` 与 qtdeclarative 的 `qml/`：
```cpp
engine.addImportPath("<qqc2_pkg>/qml");
engine.addImportPath("<qtdeclarative_pkg>/qml");
```

## 战略位置
- 下游解锁：kirigami2 5.116.0（libkirigami 硬依赖 `Qt5::QuickControls2`）

## 版本
- 5.15.2（2026-09-19 首次适配，HarmonyOS PC aarch64）
