# usbutils

## 简介
Linux USB 工具集，包含 lsusb、usbhid-dump 等命令，用于查看和管理 USB 设备。

## OHOS 适配
- 需创建 fake libudev.pc 绕过 udev 依赖检查
- OHOS SDK header 冲突：sys/socket.h 和 linux/socket.h 都定义 sockaddr_storage
- 需静态链接以规避 HarmonyOS 共享库加载限制

## 排除与替代
- lsusb.py 需要 Python 和 usb.ids 数据库

## 依赖
- libusb >= 1.0

## 功能验证
```bash
lsusb
lsusb -v
```

## 参考
- 源码: https://github.com/gregkh/usbutils
