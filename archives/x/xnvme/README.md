# xnvme — OpenHarmony 预编译包

## 概述

xnvme 是一个跨平台的 NVMe 库和工具集，提供对 NVMe 设备的用户空间访问。
支持 NVMe 管理命令、I/O 命令、区域命名空间 (ZNS) 等功能。

本目录包含 OpenHarmony (aarch64) 平台的预编译版本。

## 可用版本

| 版本 | 状态 | 构建系统 | 说明 |
|------|------|---------|------|
| 0.7.5 | published | meson | 完整编译，Linux + ramdisk 后端启用 |

## 构建特点

- 构建系统: meson + ninja
- 编译器: clang 15.0.4
- 平台: OpenHarmony aarch64 (musl libc)
- 启用后端: linux, ramdisk
- 禁用后端: spdk (需网络下载), fbsd, macos, windows, vfio

## 已知限制

- musl libc 缺少 POSIX AIO 函数，cbi_async_posix 已禁用
- SPDK/liburing/libvfn/libisal/libaio 不可用，已禁用
- 部分测试需要真实 NVMe 硬件设备才能通过

## 目录结构

```
archives/x/xnvme/
├── README.md          # 本文件（软件级说明）
└── 0.7.5/             # 版本目录
    ├── manifest.yaml  # 版本清单
    ├── notes.md       # 适配笔记
    ├── README.md      # 版本级说明
    ├── patches/       # 源码补丁
    ├── reports/       # 测试和质量报告
    └── packaging/     # 预编译包 (tar.gz)
```
