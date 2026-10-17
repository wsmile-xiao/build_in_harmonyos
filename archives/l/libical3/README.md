# libical3

## 简介
libical 3.0 版本线（iCal 3.0）：iCalendar (RFC 5545)/vCal 协议实现库，
含 GLib (GObject) 绑定 libical-glib。与 libical/4.0.1（4.x 线，无 glib
依赖）并存——多版本并存先例：boost1.84/boost1.90、kconfig 三版本。

## OHOS 适配
- 构建系统: cmake
- 编译器: clang 15.0.4
- 版本线: 3.0.20（ICAL_GLIB=ON，产出 ical/icalss/icalvcal/ical-glib）

## 依赖
- glib/2.88.3
- libxml2/2.15.3.1
- perl/5.42.2 (构建工具链)

## 参考
- 上游: https://github.com/libical/libical
- 4.x 线: archives/l/libical/4.0.1
