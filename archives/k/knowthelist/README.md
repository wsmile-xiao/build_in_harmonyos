# knowthelist - HarmonyOS PC 适配

## 软件简介

knowthelist 是一个 Qt5 派对音乐播放器（GUI 应用），支持 **DJ 模式**与**混合模式**，
适合在聚会上播放音乐。核心能力：曲库管理（SQLite）、GStreamer 音频播放、
taglib 标签读取、混音（crossfade）。

## 适配状态

| 版本 | 状态 | 说明 |
|------|------|------|
| 2.3.1 | built | 编译通过，运行时受 qt/5.15.19 无 QSQLITE 插件限制（见 2.3.1/notes.md 证据链） |

## 构建

- 构建系统: qmake（Qt5）+ make
- 依赖: qt/5.15.19, gstreamer/1.28.3, taglib/1.13.1, alsa-lib/1.2.16
- 详见 2.3.1/notes.md 与 conanfile.py

## 产物

- `bin/knowthelist` — 主程序（GUI，arm64 ELF）
- `share/pixmaps/knowthelist.png`、`share/applications/Knowthelist.desktop`
