# librsvg

librsvg 是一个用于渲染 SVG（Scalable Vector Graphics）文件的库。它基于 cairo 图形库，用于 GNOME 桌面环境和其他应用。

## 描述
librsvg 提供了一个 C API，用于解析和渲染 SVG 文件。它是 GNOME 桌面环境的核心组件之一，被广泛用于图标渲染、文档处理和其他图形应用。

## 依赖
- cairo >= 1.18.0
- cairo-gobject >= 1.18.0
- pango >= 1.50.0
- pangocairo >= 1.50.0
- gdk-pixbuf >= 2.44.6
- libxml2 >= 2.9.0
- glib >= 2.50.0
- gio >= 2.50.0
- harfbuzz >= 2.0.0
- fontconfig
- freetype2

## 版本
- 2.62.2 (built)

## 构建系统
- meson + cargo-c

## 特点
- Rust 核心（rsvg crate）
- C API 封装（librsvg-c crate）
- 支持静态库编译
- 支持 GDK-Pixbuf SVG loader

## OHOS 适配注意事项
1. 使用 OHOS SDK 的 clang-15 作为编译器（跳过 shell wrapper）
2. 需要设置 RUSTFLAGS 指定链接器
3. 需要禁用测试（-Dtests=false）避免链接问题
4. 需要禁用 introspection 和 rsvg-convert
