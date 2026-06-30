# kvantum

Kvantum 是一个基于 SVG 的 Qt 主题引擎。

## 描述
Kvantum 是一个 Qt/Qt5 主题引擎，使用 SVG 文件定义窗口装饰和控件样式。它提供了一个灵活且美观的桌面主题系统，支持自定义 SVG 主题文件。

## 已编译版本
- 1.1.8 (2026-06-01)

## 依赖
- Qt5/Qt6 Widgets
- Qt5/Qt6 Svg
- Qt5/Qt6 X11Extras (optional, disabled on HarmonyOS)

## 特性
- SVG 主题定义
- 样式插件 (kvantum style)
- 预览工具 (kvantumpreview)
- manager 工具 (未编译，因 X11 依赖)

## 注意事项
- X11 相关功能已通过 `#ifdef __OHOS__` 守卫跳过
- kvantummanager 因缺少 Qt6Svg 完整库而跳过编译