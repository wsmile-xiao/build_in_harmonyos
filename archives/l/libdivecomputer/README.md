# libdivecomputer

## 简介

libdivecomputer（Jef Driesen）是跨平台 C 库，用于与各厂商潜水电脑
（dive computer）通信：支持下载潜水剖面日志、读取/写入设备设置、
时间同步与固件升级，覆盖 Suunto、Suunto EON/Stinger、Uwatec Aladin/
Smart、Oceanic、Mares、Cressi、Shearwater、HW/Heinrichs Weikamp、
Scubapro、Zeagle、Reefnet 等百余型号，串口/USB/USBHID/Bluetooth 多种
传输方式，并含各家族的二进制数据解析器（parser）。

## OHOS 适配（0.9.0）

- autotools + libtool 工程；`libdivecomputer.la` 默认同时构建
  static/shared，`dctool` 示例工具随 `--enable-examples`（默认开）安装至 bin。
- tarball 内 config.sub（2022-01-03）不识别 `aarch64-unknown-linux-ohos`，
  以 `patches/0001-config.sub-ohos.patch` 接受 `ohos*`/`linux-ohos*`
  （与 acpid/adplug 先例同根因同修法）。
- 传输后端全可选、全部优雅降级（缺失时运行时返回
  `DC_STATUS_UNSUPPORTED`），构建不以任何潜水电脑硬件为前提：
  - serial：非 Windows 恒开，仅标准 POSIX termios（OHOS musl 提供）
  - usb：`with_libusb`（默认开，libusb/1.0.27 制品仓有 ohos 二进制）
  - usbhid：hidapi 缺省时回退纯 libusb（USE_LIBUSB）
  - irda：头探测（linux/irda.h），OHOS 自然缺失 → 空操作
  - bluetooth：`with_bluez`（默认关；OHOS 未验证 bluez 库消费场景）
  - ble：上游 0.9.0 硬编码关闭（仅公共 API 壳）
- 上游零自动化测试（无 check/test 目标、无 gtest/pytest/ctest）；
  `examples/dctool` 为手动 CLI 工具。test_package 以硬件无关公共 API
  （version/context/descriptor 迭代器/合成剖面 parser）做消费者验证。

## 依赖

- 运行时核心库：无强制依赖
- 可选：libusb（USB/USBHID 传输）、hidapi、bluez（Bluetooth Classic）

## 功能验证

```bash
# 消费者冒烟测试（test_package 自动执行，无需潜水电脑/串口/USB/蓝牙）
./test_package   # 20 项 CHECK：版本、context、传输掩码、设备库、离线解析器
```

## 参考

- 官网: https://www.libdivecomputer.org/
- 源码: https://github.com/libdivecomputer/libdivecomputer/releases/download/v0.9.0/libdivecomputer-0.9.0.tar.gz
- Issues: https://github.com/libdivecomputer/libdivecomputer/issues
