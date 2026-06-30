# AirSpy Host

AirSpy 用户态驱动及配套工具，用于软件定义无线电（SDR）。提供 libairspy 共享库和 airspy_info、airspy_rx 等命令行工具。

## 功能概述

- **libairspy**: AirSpy SDR 设备的用户态 USB 驱动库
- **airspy_info**: 查询设备信息和库版本
- **airspy_rx**: 接收 IQ 采样数据

## 来源

- 源码仓库: https://github.com/airspy/airspyone_host
- 版本标签: v1.0.10

## 许可证

GPL-2.0-or-later（部分组件为 BSD 许可）

## OHOS 适配

### 关键适配点

1. **CMake UNIX 变量问题**: CMake 在 HarmonyOS 上不设置 `UNIX` 变量（系统未被识别），导致库和头文件的 install 目标被跳过。解决方案：将 `if(${UNIX})` 改为 `if(NOT WIN32)`。

2. **CMAKE_SYSTEM_NAME 设置**: CMake 输出 "System is unknown to cmake"。设置 `CMAKE_SYSTEM_NAME=Linux` 可解决兼容性问题。

3. **LD_LIBRARY_PATH 陷阱**: 不要设置 `LD_LIBRARY_PATH` 包含 `~/usr/local/lib`，会导致 lld 链接器找不到 `libxml2.so.16`。系统默认路径已正确。

4. **CMake 版本兼容**: 项目使用 `cmake_minimum_required(VERSION 2.8)`，需设置 `CMAKE_POLICY_VERSION_MINIMUM=3.5` 以兼容 CMake 4.x。

## 依赖关系

### 编译依赖
- **libusb-1.0** (1.0.27): 使用 cmd-pkgs 预编译包安装

### 运行依赖
- **pthread**: 系统内置
- **libusb-1.0**: 运行时 USB 设备访问

## 参考资料

- 官方仓库: https://github.com/airspy/airspyone_host
- AirSpy 官网: https://airspy.com

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| [1.0.10](./1.0.10/) | built | 2026-06-29 |
