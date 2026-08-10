# disomaster

DISOMaster 是 deepin 开发的 Qt 封装库，提供光盘操作功能（刻录、擦除、检查、ISO 读写等）。

上游直接调用 libisoburn C API，鸿蒙平台上使用 xorriso 命令行替代（通过 QProcess 调用）。

## 功能概述
- 获取光盘设备属性（介质类型、容量、速度等）
- 文件暂存与刻录（支持 Joliet / Rock Ridge 扩展）
- 擦除可重写光盘
- 介质质量检查
- ISO 镜像读取与写入

## 依赖关系
- **编译依赖**: Qt5 Core (qt5-qtbase/5.15.2)
- **运行依赖**: xorriso（OHOS 平台提供预构建二进制）

## OHOS 适配
- 上游使用 qmake 构建系统，改为 CMake
- 上游使用 libisoburn C API，改为 QProcess 调用 xorriso CLI
- xorriso 预构建包来自 PR !831

## 参考资料
- 源码: https://github.com/linuxdeepin/disomaster
- 许可证: GPL-3.0-or-later
