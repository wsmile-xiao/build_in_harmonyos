# E083 — OHOS SDK头文件sockaddr_storage重复定义冲突

## 问题概述

OHOS SDK中`sys/socket.h`（musl libc）和`linux/socket.h`（内核UAPI）都定义了`struct sockaddr_storage`，导致同时包含时出现重复定义错误。

## 错误特征

```
error: redefinition of 'struct sockaddr_storage'
note: previous definition is here
```

## 根本原因

1. musl libc的`sys/socket.h`使用32位`sa_family_t`定义sockaddr_storage
2. 内核UAPI的`linux/socket.h`使用16位`__kernel_sa_family_t`定义sockaddr_storage
3. 两处定义不兼容，同时包含导致编译失败

## 解决方案

**方案一：添加头文件守卫**
```c
#define _UAPI_LINUX_SOCKET_H  // 阻止linux/socket.h重复定义
#include <sys/socket.h>
```

**方案二：条件编译选择头文件**
```c
#ifdef __OHOS__
#include <sys/socket.h>
#else
#include <linux/socket.h>
#endif
```

## 受影响软件

libusb, usbutils 等网络相关库

## 补丁示例

libusb补丁：`0001-linux_netlink-fix-sockaddr_storage-conflict.patch`

## 发现时间

2026-04-27，机器E编译任务
