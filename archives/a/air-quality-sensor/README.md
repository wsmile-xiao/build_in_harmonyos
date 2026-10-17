# air-quality-sensor

**用户态驱动**：读取 AppliedSensor Indoor Air Monitor（USB CO2 传感器）的空气质量数据。

## 功能概述

- 通过 libusb-1.0 枚举 USB 设备，识别 AppliedSensor Indoor Air Monitor（USB Vendor 0x03eb / Product 0x2013）
- 读取传感器返回的 CO2 浓度值，按阈值分级为 GREEN / YELLOW / RED / NO_DATA 并输出