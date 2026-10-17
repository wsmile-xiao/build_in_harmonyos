# picotool

Raspberry Pi 官方的 Pico 系列开发工具（C++，BSD-3-Clause）。

## 功能

- 与 RP2040/RP2350 设备通过 USB（picoboot 协议）交互：load/save/erase/reboot
- 解析 ELF/UF2/BIN/HEX 固件文件，提取 binary_info 信息（`picotool info`）
- 分区表管理（partition create/load）、块设备文件系统操作（bdev format/ls/cp）
- OTP（一次性可编程存储）读写

## 平台适配（HarmonyOS PC aarch64）

| 版本 | 状态 | 说明 |
|------|------|------|
| 2.2.0 | published | 首次适配 |
| 2.3.0 | published | 跟进上游版本 |

- 构建系统：CMake（bundled 依赖源码自带）
- 运行依赖：libusb（制品仓 conan 包）；USB 设备功能需系统侧 USB 主机权限支持
- pico-sdk：构建期以 `PICO_SDK_PATH` 方式从上游官方源获取配套版本

## 命令

见 `commands.json`（hicmd 格式声明）。

## 参考

- 上游仓库：https://github.com/raspberrypi/picotool
- pico-sdk：https://github.com/raspberrypi/pico-sdk
