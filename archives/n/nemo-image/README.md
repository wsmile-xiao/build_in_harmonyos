# nemo-image

Nemo 文件管理器的图像缩放/旋转右键菜单扩展（上游 linuxmint/nemo-extensions
的 nemo-image-converter 组件，C 语言，GPL-2.0-or-later）。

为 Nemo 中选中的图像文件添加 **Resize Images**（缩放）与 **Rotate
Images**（旋转）上下文菜单项，弹出 GTK3 对话框批量处理。

OHOS 适配交付两件套：
- `lib/nemo/extensions-3.0/libnemo-image-converter.so` — 扩展模块（Nemo
  经 GModule/dlopen 加载）
- `lib/libnemo-extension.so` — vendored Nemo 扩展 ABI 库精简子集（上游
  位于 nemo 主包源码树、制品仓无独立包；本扩展调用的全部符号集合）

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 6.6.0 | built | 上游 nemo-extensions 6.6.0 统一发版 tag；OHOS arm64 |

## 依赖

- gtk/3.24.43（OHOS 预编译）
- glib/2.84.0.1（gtk 闭包对齐，提供 proxy libintl）
