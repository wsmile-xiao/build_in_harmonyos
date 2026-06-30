# ykpers 1.20.0 编译笔记

## 编译日期
2026-06-04

## 编译状态
**built** - 编译成功，预编译包制作完成

## 编译环境
- 平台: HarmonyOS Kernel 1.12.0, aarch64
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)

## 依赖项
- libyubikey 1.13 (手动编译安装)
- libusb 1.0.27 (手动编译安装，需特殊处理)
- json-c 0.18 (系统已安装)

## 遇到的问题及解决方案

### 1. config.guess 无法识别 HarmonyOS
**问题**: configure 报错 "cannot guess build type"
**解决方案**: 在 `build-aux/config.guess` 中添加 HarmonyOS 平台识别:
```
aarch64:HarmonyOS:*:*)
    echo aarch64-harmony-linux
    exit ;;
```

### 2. HMDFS SELinux 权限问题
**问题**: autotools 无法创建临时文件
**解决方案**: `sed -i 's/umask 077/umask 022/g' configure`

### 3. TRUE/FALSE 未定义
**问题**: 编译报错 "use of undeclared identifier 'TRUE'"
**解决方案**: 在 `ykpers-json.c` 中添加宏定义:
```c
#ifndef TRUE
#define TRUE 1
#endif
#ifndef FALSE
#define FALSE 0
#endif
```

### 4. 链接器重复符号错误
**问题**: `duplicate symbol: optstring` 和 `duplicate symbol: usage`
**解决方案**: 在 `ykpers-args.h` 中将变量定义改为 extern 声明:
```c
extern const char *usage;
extern const char *optstring;
```

### 5. libusb 编译失败（系统头文件冲突）
**问题**: `linux/socket.h` 和 `sys/socket.h` 重复定义 `sockaddr_storage`
**解决方案**: 在 `libusb/os/linux_netlink.c` 中添加:
```c
#define _UAPI_LINUX_SOCKET_H
typedef unsigned short __kernel_sa_family_t;
#include <linux/netlink.h>
```

## 安装位置
- 库文件: ~/usr/local/lib/libykpers-1.so.1.20.0
- 头文件: ~/usr/local/include/ykpers-1/
- 二进制: ~/usr/local/bin/ykpersonalize, ykchalresp, ykinfo

## 验证结果
- ykpersonalize --version 可运行（USB 错误因无 YubiKey 设备）

---
**编译结束**: 2026-06-04 10:15
**最终状态**: built
---

**编译结束**: 2026-06-04 10:16
**最终状态**: built
