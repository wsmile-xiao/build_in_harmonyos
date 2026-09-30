# libdfu-ahp

> 用于编程 USB DFU 设备的 C 库。

## 简介

`libdfu-ahp` 提供 DFU 固件下载、上传和设备控制接口。当前归档锁定 AtomGit 任务要求的 2022-12-15 上游提交，不跟随后续 `master` 变化。

## OHOS 适配要点

- 构建系统为 CMake，依赖 `libusb-1.0`、线程库和数学库。
- 归档补丁修正了上游绝对安装目录，使 Conan staging 前缀能正确收集库文件和头文件。
- 真实 DFU 设备功能需要鸿蒙 PC 真机和可用 USB 外设；无设备时只能验证编译、链接和错误路径。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| libusb | 1.0.27 | USB 访问库 |

## 功能验证

消费者用例调用公开 API `dfu_flash_filename`，以不存在的固件路径验证 `ENODEV` 错误返回。设备刷写路径需在真机上继续验证。

## 参考

- [源码仓库](https://github.com/ahp-electronics/libdfu)
- [DFU 规范](https://usb.org/document-library/device-firmware-upgrade-11-dfu-specification)
