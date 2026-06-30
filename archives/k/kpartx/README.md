# kpartx

Create device maps from partition tables.

## 描述

kpartx 是 multipath-tools 项目的一部分，用于从分区表创建设备映射。
它读取磁盘分区表并为每个分区创建设备映射器映射。

## 版本

- 0.14.3 (multipath-tools v0.14.3) - 2026-06-11

## 依赖

- libdevmapper (device mapper library)

## 功能限制

在鸿蒙系统上，kpartx 需要 device-mapper 内核模块支持才能正常工作。
当前仅验证了编译可行性，实际功能依赖于内核模块。

## 安装

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- kpartx 0.14.3
```

注意：预编译包包含 libdevmapper 作为依赖库。