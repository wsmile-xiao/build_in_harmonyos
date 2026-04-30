# libpciaccess 0.17 for HarmonyOS/OpenHarmony (aarch64)

## 概述

libpciaccess 是 X.Org 项目的 PCI 设备访问库，提供跨平台的 PCI 设备信息查询接口。本预编译包为 HarmonyOS/OpenHarmony (aarch64) 平台编译。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | libpciaccess |
| 版本 | 0.17 |
| 下载地址 | https://xorg.freedesktop.org/releases/individual/lib/libpciaccess-0.17.tar.gz |
| 官方文档 | https://gitlab.freedesktop.org/xorg/lib/libpciaccess |

## 编译信息

| 项目 | 值 |
|------|-----|
| 构建系统 | Meson |
| 编译器 | Clang 15.0.4 (OHOS SDK) |
| 平台 | aarch64-linux-ohos |
| 安装路径 | ~/usr/local |

## 产品列表

| 类型 | 文件 |
|------|------|
| 共享库 | lib/libpciaccess.so.0.11.1 |
| 工具 | bin/scanpci |
| 头文件 | include/pciaccess.h |
| pkg-config | lib/pkgconfig/pciaccess.pc |

## 安装方法

```bash
# 下载预编译包
curl -fsSL https://your-repo/libpciaccess-0.17-ohos-aarch64.tar.gz | tar xz

# 安装到 ~/usr/local (默认)
cd libpciaccess-0.17
./install.sh

# 或指定自定义路径
PREFIX=/custom/path ./install.sh
```

## 使用示例

```bash
# 查看 PCI 设备
scanpci

# 编译使用 libpciaccess 的程序
clang -o my_pci_tool my_pci_tool.c -lpciaccess
```

## 依赖

无外部库依赖，仅需 libc.so。

## 注意事项

- scanpci 工具需要 root 权限才能访问 /sys/bus/pci 设备
- 鸿蒙系统的 PCI 设备访问可能受到 SELinux 限制
- 如遇执行问题，请检查 ELF 文件是否已签名

## 编译难度

🟡 中等 - meson 构建系统，无需补丁

## 更新日期

2026-04-27