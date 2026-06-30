# parole 4.20.0 编译笔记

## 基本信息
- 软件: parole (XFCE媒体播放器)
- 版本: 4.20.0
- 构建系统: meson
- 状态: **failed**

## 编译过程
- meson setup失败: 依赖libxfce4ui-2未找到
- 缺失依赖: libxfce4ui-2, xfconf, libnotify, taglib
- 这些XFCE桌面环境库没有预编译包

---
**编译结束**: 2026-06-05
**最终状态**: failed
**失败原因**: XFCE桌面环境依赖链缺失
