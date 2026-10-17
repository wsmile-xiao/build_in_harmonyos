# kirigami-gallery

KDE Release Service 官方的 Kirigami UI 框架展示应用：一个 QML 组件画廊演示
程序，展示 Kirigami 6（Card/OverlaySheet/ActionToolBar/Columns/TabBar 等）
与 KItemModels 的用法，是学习与验证 Kirigami/QML 组件栈功能完整性的参考
应用。

- 上游: https://invent.kde.org/graphics/kirigami-gallery
- 发布渠道: KDE Release Service（release-service/26.04.0）
- 许可: LGPL-2.0-or-later（C++ 源）/ GPL-3.0-or-later（部分 QML）
- 语言: C++ (2 个源文件) + QML (56 个界面文件，经 resources.qrc 内嵌)
- 构建系统: CMake + ECM
- 类型: GUI 应用（可执行文件 kirigami2gallery，R38 已声明 commands.json）

## 适配版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 26.04.0 | built | 首次适配 aarch64-linux-ohos |

## 依赖（均已在 ohpcd 制品仓发布）

- qtbase/6.11.1（Core/Gui/Widgets + offscreen QPA 插件）
- qtdeclarative/6.11.1（Qml/Quick/QuickControls2/QML 运行时模块）
- qtsvg/6.11.1、qtshadertools/6.11.1
- kirigami/6.26.0（KF6Kirigami + org.kde.kirigami QML 模块）
- kitemmodels/6.18.0.1（KF6ItemModels + org.kde.kitemmodels QML 模块）
- ecm/6.26.0（tool_requires）
