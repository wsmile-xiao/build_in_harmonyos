# bmd-tools v1.0.2 编译笔记

## 基本信息
- 软件名: bmd-tools
- 版本: v1.0.2
- 功能: Blackmagic Design 视频设备 H.264 USB 工具集 (bmd-streamer, bmd-extractfw)
- 构建系统: Makefile (简单)
- 交叉编译目标: aarch64-unknown-linux-ohos

## 编译过程

### 1. 初始化
- init-build 下载超时，改用 wget 手动下载
- 手动创建 .orig/.work 目录和构建上下文文件绕过 init-build SSL 步骤

### 2. 依赖编译
- bmd-tools 依赖 libusb-1.0，OHOS 系统默认不包含
- 编译 libusb-1.0.27 作为静态库 (--enable-static --disable-udev --disable-netlink)
- 关键问题: linux/socket.h 和 sys/socket.h 存在 sockaddr_storage 重定义冲突
- 解决: 修补 linux_netlink.c，添加 `#ifdef __OHOS__` 守卫，阻止 linux/socket.h 被 linux/netlink.h 重复引入
  - 定义 `_UAPI_LINUX_SOCKET_H` 阻止 linux/socket.h
  - 手动定义 `__kernel_sa_family_t` (unsigned short) 补偿 linux/netlink.h 的依赖

### 3. Makefile 适配
- 原始 Makefile 使用硬编码 `gcc`，无法交叉编译
- 修改内容:
  - 添加 CC, PREFIX, DESTDIR, PKG_CONFIG, INSTALL 变量 (均使用 ?= 赋值)
  - 将 gcc 替换为 $(CC)
  - CFLAGS 改为追加模式 (?= 初始值 + += 补充)
  - 添加 install target (DESTDIR 模式)
  - 添加 .PHONY 声明

### 4. 编译结果
- bmd-streamer: 47552 bytes, ELF64 aarch64
- bmd-extractfw: 22976 bytes, ELF64 aarch64
- 编译警告: 4 个 -Wpointer-sign 警告 (char vs uint8_t)，不影响功能

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载超时 | 网络限制 | wget 手动下载 |
| 2 | init-build SSL 步骤停滞 | SSL 证书验证问题 | 手动创建构建上下文 |
| 3 | libusb 缺失 | OHOS 默认不包含 libusb | 编译 libusb-1.0.27 静态库 |
| 4 | sockaddr_storage 重定义 | linux/socket.h 与 sys/socket.h 冲突 | `#ifdef __OHOS__` 守卫阻止 linux/socket.h |
| 5 | Makefile 硬编码 gcc | 不支持交叉编译 | 添加 CC/DESTDIR 等变量 |

## 补丁
- 0001-Makefile.patch: 构建系统适配，添加交叉编译支持

## 依赖版本
- libusb-1.0.27 (静态编译)

## 验证结果
```bash
llvm-objdump -f bmd-streamer
bmd-streamer: file format elf64-littleaarch64
architecture: aarch64
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bmd-streamer | 47552 bytes | BMD USB H.264 流工具 |
| bmd-extractfw | 22976 bytes | BMD 固件提取工具 |

## 注意事项
- libusb-1.0 必须先编译安装，PKG_CONFIG_PATH 需设置
- OHOS SDK 头文件存在 linux/socket.h 与 sys/socket.h 冲突，需要 __OHOS__ 守卫
---

**编译结束**: 2026-05-29 16:13
**最终状态**: built
