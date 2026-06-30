# libqrtr-glib

## 简介

libqrtr-glib 是一个基于 GLib 的 QRTR（Qualcomm Remote Processor Transport）协议库，用于与 Qualcomm 调制解调器通信。

## OHOS 适配

### 关键问题

1. **sockaddr_storage 重定义冲突**：OHOS SDK 的 `sys/socket.h` 和 `linux/socket.h` 都定义了 `sockaddr_storage`，导致编译错误。

2. **解决方案**：
   - 先包含 `sys/socket.h`
   - 定义 `_UAPI_LINUX_SOCKET_H` 防止 `linux/socket.h` 被包含
   - 手动定义 `__kernel_sa_family_t` 和 `__packed`

### 与 Linux 的差异

- Linux：无 sockaddr_storage 冲突
- OHOS：需要特殊处理头文件包含顺序

## 依赖

- glib-2.0 >= 2.0

## 功能验证

```bash
pkg-config --modversion qrtr-glib
```

## 参考

- 源码仓库：https://github.com/linux-mobile-broadband/libqrtr-glib