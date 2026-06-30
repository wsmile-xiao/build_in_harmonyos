# libftdi1

## 简介

libFTDI 是一个开源库，用于与 FTDI 芯片通信。它通过 libusb 在用户空间与 FTDI USB 设备通信，无需内核驱动。

## 支持的芯片

- FT230X
- FT4232H / FT2232H
- FT232R / FT245R
- FT2232L / FT2232D / FT2232C
- FT232BM / FT245BM (以及 BL/BQ 变种)
- FT8U232AM / FT8U245AM

## 编译版本

| 版本 | 状态 | 编译日期 | 补丁数 | 产物 |
|------|------|----------|--------|------|
| 1.5 | built | 2026-06-05 | 0 | libftdi1-1.5-ohos-aarch64.tar.gz (728KB) |

**功能测试**: 2026-06-05 全项通过，符合上库要求

## 依赖

- **libusb-1.0**: USB 设备通信库（运行时依赖）
- **libconfuse**: 配置文件解析库（ftdi_eeprom 工具需要）

## 功能

1. **libftdi1**: 核心库，提供 FTDI 芯片通信接口
2. **ftdi_eeprom**: EEPROM 配置工具，用于读写 FTDI 芯片的 EEPROM

## 注意事项

1. **平台支持**: 支持 Linux、Windows、MacOS X 和 BSD
2. **HMDFS 限制**: 在鸿蒙系统上部署时需注意文件系统权限问题
3. **ELF 签名**: 预编译包已包含 ELF 签名，可直接执行

## 许可证

- 核心库: LGPL 2.1 (not any later)
- ftdi_eeprom: GPL 2.0 (not any later)

## 参考链接

- 官方网站: https://www.intra2net.com/en/developer/libftdi/index.php
- 下载页面: https://www.intra2net.com/en/developer/libftdi/download.php
- FTDI 官网: https://www.ftdichip.com/