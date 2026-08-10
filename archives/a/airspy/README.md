# AirSpy (libairspy)

AirSpy 用户态 USB 驱动库 libairspy，用于软件定义无线电（SDR）。AirSpy 硬件通过 libusb-1.0 与主机通信，本库提供打开设备、设置采样率与频率、启动/停止 IQ 接收等 API。

## 功能概述

- **libairspy**: AirSpy SDR 设备的用户态 USB 驱动共享/静态库
- 配套工具（airspy_info / airspy_rx 等）在上游同仓 `airspy-tools/` 下，本配方的 `package_type=library` 仅产出库与头文件

## 来源

- 源码仓库: https://github.com/airspy/airspyone_host
- 版本标签: v1.0.10

## 许可证

GPL-2.0-or-later（libairspy 部分文件 BSD 许可）

## OHOS 适配

### 关键适配点

1. **CMake UNIX 变量问题**: CMake 在 HarmonyOS 上不设置 `UNIX` 变量（系统未被识别），导致 libairspy 的 install 目标被 `if(${UNIX})` 跳过。解决方案：将 `if(${UNIX})` 改为 `if(NOT WIN32)`。

2. **CMAKE_SYSTEM_NAME 设置**: CMake 输出 "System is unknown to cmake"。设置 `CMAKE_SYSTEM_NAME=Linux` 可解决兼容性问题（E092）。

3. **CMake 版本兼容**: 项目使用 `cmake_minimum_required(VERSION 2.8)`，需设置 `CMAKE_POLICY_VERSION_MINIMUM=3.5` 以兼容 CMake 4.x。

## 依赖关系

### 编译依赖
- **libusb-1.0** (1.0.27): 使用 cmd-pkgs 预编译包安装，声明为系统库

### 运行依赖
- **pthread**: 系统内置
- **libusb-1.0**: 运行时 USB 设备访问

## 参考资料

- 官方仓库: https://github.com/airspy/airspyone_host
- AirSpy 官网: https://airspy.com

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| [1.0.10](./1.0.10/) | built | 2026-08-08 |
