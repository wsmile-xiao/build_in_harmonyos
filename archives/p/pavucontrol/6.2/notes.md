# pavucontrol 6.2 编译笔记

## 基本信息
- 软件: pavucontrol (PulseAudio音量控制GTK版)
- 版本: 6.2（最新release版）
- 构建系统: meson
- 状态: **failed**

## 编译过程
- meson setup失败: 依赖gtkmm-4.0未找到
- 缺失关键依赖: gtkmm-4.0 (GTK4 C++包装), libpulse-mainloop-glib
- 可用依赖: libpulse 16.1, sigc++-3.0 3.6.0, json-glib-1.0 1.6.6

## 替代方案
- pavucontrol-qt 2.4.0（Qt版）已成功编译，功能类似

---
**编译结束**: 2026-06-05
**最终状态**: failed
**失败原因**: gtkmm-4.0和libpulse-mainloop-glib缺失
