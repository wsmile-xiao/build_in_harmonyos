# libevt

用于访问 Windows 事件日志 (EVT) 格式的库。

## 简介

libevt 是一个 C 库，提供对 Windows 事件日志（Windows Event Log，EVT 格式，Windows 2000/XP/2003 时代格式）的读取访问，是 libyal 取证工具生态的一员。EVT 日志以二进制格式存储事件记录，包含事件 ID、来源、类别与描述字符串等。

该项目还包含两个终端工具：
- **evtinfo**: 显示 EVT 文件基本信息（使用 libevt/头信息工具集）
- **evtexport**: 导出 EVT 日志记录为文本/CSV 等格式

新版 Windows (Vista 以后) 使用 EVTX 格式，由姊妹库 libevtx 支持。

## 官网

https://github.com/libyal/libevt

## 许可证

LGPL-3.0-or-later
