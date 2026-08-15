# pango

Pango 是一个用于布局和渲染文本的库，强调国际化支持。它是 GTK+ 的核心文本渲染引擎。

## 描述

Pango 提供了高质量的文本渲染，支持：
- 多语言文本布局
- 复杂脚本支持（如阿拉伯语、泰语）
- 字体选择和渲染
- 与 Cairo 图形库集成

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|---------|
| 1.50.14 | published | 2026-08-14 |

## 依赖

核心依赖：
- glib-2.0
- harfbuzz
- freetype2
- fontconfig
- fribidi

可选依赖：
- cairo（用于 Cairo 后端）
- libthai（泰语支持）

## 编译说明

使用 meson 构建系统。关键配置选项：
- `-Dcairo=enabled`：启用 Cairo 支持
- `-Dxft=disabled`：禁用 Xft（鸿蒙无 X11）
- `-Dintrospection=disabled`：禁用 GObject introspection

## 注意事项

1. cairo 必须启用 freetype 支持，否则 pango 无法找到 cairo-ft 后端
2. 如果缺少 cairo-ft.pc，需要手动创建或在重新编译 cairo 时确保生成