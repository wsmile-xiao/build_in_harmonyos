# wmusic

**WindowMaker dockapp for controlling MPRIS-compatible media players**

## 简介

wmusic 是一个 WindowMaker dockapp，通过 MPRIS D-Bus 接口控制兼容的媒体播放器
（如 playerctl 所支持的播放器），支持播放/暂停/上下曲/音量调节与曲目信息显示。
基于 libdockapp（X11）与 playerctl（GObject）构建。

- 上游主页: https://www.dockapps.net/wmusic
- 源码: https://www.dockapps.net/download/wmusic-2.1.1.tar.gz

## 编译状态

| 版本 | 状态 | 构建系统 | 日期 |
|------|------|----------|------|
| 2.1.1 | built | autotools | 2026-09-29 |

## 依赖

- libdockapp/0.7.3
- playerctl/2.4.1（间接依赖 glib/2.84.0.1）
- libxpm/3.5.17、libx11/6.4.0、libxext/6.4.0、xorgproto/2025.1

## 使用

```bash
# wmusic 是 X11 GUI dockapp，需在 X server（如 WindowMaker）环境下运行
wmusic --help
wmusic --version
```

## 注意

- 鸿蒙 PC 无 X server 时，wmusic 启动会因 `XOpenDisplay` 失败退出，属预期行为；
  需配合 X 环境使用。
- 消费者运行时需 D-Bus session bus（playerctl 依赖 MPRIS 接口）。
