# libuvc

> 跨平台 USB Video Class (UVC) 设备访问库，基于 libusb-1.0。

## 简介

libuvc 是一个跨平台库，支持 UVC 设备（如消费级 webcam）的枚举、控制与视频流。提供 UVC 设备发现与管理 API、视频流（异步回调和同步轮询）、标准设备设置读写、多种帧格式（RGB/YUV/JPEG 等）间转换。上游在 Mac/Linux 测试，可移植到 Windows 和部分 BSD。

## OHOS 适配要点

- **CMake 系统识别**：HarmonyOS 未被 CMake 识别（E092），配方设置 `CMAKE_SYSTEM_NAME=Linux` 让 pthread 探测的 `if(UNIX AND NOT APPLE)` 分支生效。
- **libusb 探测**：上游 `FindLibUSB.cmake` 依赖 pkg-config，headless OHOS 不可靠；配方改写为从 Conan 注入的缓存变量构造 `LibUSB::LibUSB` 目标。
- **运行时 USB 能力**：libuvc 通过 libusb 做 USB I/O。在鸿蒙普通应用沙箱中，USB 设备枚举/I/O 受 SELinux neverallow 阻断（详见 [libusb](../libusb/) 能力评估）。libuvc 编译链接、库初始化、帧处理 API 均可用；实际 USB 视频流需以系统服务（`usb_host` SELinux 域）运行。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| libusb | 1.0.27 | USB 设备访问库（制品仓） |
| pthread | 系统 | 事件处理线程 |

## 功能验证

```bash
# 消费者冒烟测试（无需 USB 硬件，验证帧处理 API）
conan test archives/l/libuvc/0.0.7/test_package libuvc/0.0.7 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 参考

- [libuvc 官方仓库](https://github.com/libuvc/libuvc)
- [libuvc 文档](https://libuvc.github.io/libuvc/)

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| [0.0.7](./0.0.7/) | built | 2026-08-13 |
