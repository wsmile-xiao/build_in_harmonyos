# libusbsio

## 简介

NXP LIBUSBSIO：USB 串行 I/O 库。面向 LPC-Link2 / MCU-Link 调试探针的用户态主机库，
将 API 调用转换为 USB-HID 报文，经探针的 I²C / SPI / GPIO 接口与目标器件通信。
纯 C 轻件（2 个编译单元），Linux 后端基于内嵌 hidapi（hidraw）。

## OHOS 适配

- **版本**：2.1.13（等价源见 2.1.13/notes.md：上游 Intronics 仓库已删除，
  Linux 产物线 C 库与官方 PyPI 2.1.13 wheel 内嵌 so 逐字节一致，源用
  monwarez/libusbsio@8577280 公开快照）
- **构建**：配方内直接复现上游 makefile Linux 目标（clang 交叉编译，
  `-Wl,-soname` 共享库）；零补丁
- **依赖**：libudev-zero/1.0.4（静态链入，替代 OHOS 缺失的 systemd libudev）；
  不依赖 libusb（hidraw 后端）
- **测试**：test_package 无硬件 CI profile（API 面/版本契约/枚举路径/错误契约）；
  上游 testapp 为交互式硬件测试，逐项定性见版本 notes.md

## 依赖

- libudev-zero/1.0.4（构建+运行，枚举后端）
