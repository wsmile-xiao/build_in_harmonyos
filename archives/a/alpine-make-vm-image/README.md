# alpine-make-vm-image

alpine-make-vm-image 是一个创建 Alpine Linux 虚拟机镜像的工具，支持多种虚拟化平台。

## 描述

alpine-make-vm-image 基于 Alpine Linux 创建可用于 QEMU、VirtualBox 等虚拟化平台的 VM 镜像。它自动化了 Alpine Linux 的安装和配置过程。

## 已编译版本

- 0.13.4 (2026-05-30)

## 特性

- 创建 Alpine Linux VM 镜像
- 支持 QEMU、VirtualBox 等平台
- 自动化安装配置

## 使用方法

```bash
alpine-make-vm-image --image-size 2G --packages "openssh" output.qcow2
```