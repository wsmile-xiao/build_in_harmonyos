# bmd-tools

> Blackmagic Design USB H.264 streaming and firmware extraction tools

## 简介

bmd-tools 提供两个工具：bmd-streamer（USB H.264 视频流工具）和 bmd-extractfw（固件提取工具），用于与 Blackmagic Design USB 设备交互。依赖 libusb-1.0 进行 USB 通信。

## OHOS 适配要点

- Makefile 硬编码 gcc，需添加 CC/PREFIX/DESTDIR/INSTALL 变量和 install target
- OHOS SDK 的 linux/socket.h 和 sys/socket.h 存在 sockaddr_storage 重定义冲突，需用 #ifdef __OHOS__ 守卫
- libusb-1.0 需单独编译安装（--enable-static --disable-udev --disable-netlink）

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| libusb-1.0 | 1.0.27 | USB 通信库 |

## 功能验证

```bash
bmd-streamer --help
bmd-extractfw --help
```

## 参考

- [源码仓库](https://github.com/fabled/bmd-tools)