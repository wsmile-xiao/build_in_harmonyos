# librtlsdr

librtlsdr 是一个用于 RTL2832 基于 DVB dongle 的软件定义无线电(SDR)接收器库。

## 描述

rtl-sdr 项目将 Realtek RTL2832 基于 DVB dongle 转换为 SDR 接收器。

## 版本

- 2.0.2 (当前编译版本)

## 依赖

- libusb-1.0 >= 1.0

## 编译版本

- **2.0.2**: 2026-06-10
  - 构建系统: CMake
  - 编译器: Clang 15.0.4
  - 依赖: libusb/1.0.27

## 补丁

编译 v2.0.2 需要以下补丁:
- `0001-src-librtlsdr.c.patch`: 修复 libusb.h include 路径
- `0002-src-rtl_adsb.c.patch`: 禁用 musl 不支持的 pthread_cancel
- `0003-src-rtl_fm.c.patch`: 修复 libusb.h include 路径
- `0004-src-rtl_power.c.patch`: 修复 libusb.h include 路径

## 用途

SDR 应用、无线电信号分析、频谱监控等。

## 参考

- 官方项目: https://osmocom.org/projects/rtl-sdr/wiki
- GitHub: https://github.com/osmocom/rtl-sdr