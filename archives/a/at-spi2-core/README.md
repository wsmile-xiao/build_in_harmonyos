# at-spi2-core

ATK accessibility toolkit 和 AT-SPI D-Bus 桥接库，用于辅助功能支持。

## 基本信息

- **语言**: C
- **类型**: 辅助功能库
- **官方网站**: https://wiki.gnome.org/Accessibility
- **源码**: https://gitlab.gnome.org/GNOME/at-spi2-core

## 功能特性

- ATK 辅助功能工具包
- AT-SPI D-Bus 桥接
- 屏幕阅读器支持
- 无障碍 API

## 版本信息

| 版本 | 状态 | 构建系统 | 依赖 |
|------|------|----------|------|
| 2.58.3-r0 | published | meson | dbus, glib |

## 依赖

- dbus-1 >= 1.14.10
- glib-2.0 >= 2.82.4
- libxml-2.0 >= 2.15.3

## 使用说明

```bash
pkg-config --modversion atk atspi-2 atk-bridge-2.0
# 输出: 2.58.3
```

## 编译说明

- 使用 meson 构建系统
- X11 支持已禁用（缺少 xtst 预编译包）
- 需要 PKG_CONFIG_PATH 包含 harmonybrew/lib/pkgconfig（zlib.pc）
- 配置选项: `meson setup build --prefix=$DEFAULT_PREFIX --wrap-mode=nodownload -Dx11=disabled`