# cloud-utils

cloud-utils 是一组用于与云镜像和云实例交互的命令行工具。

## 描述

cloud-utils 提供了创建、修改和管理云虚拟机镜像的工具集。常用工具包括 growpart（扩展分区）、cloud-localds（创建本地数据源）等，广泛用于 OpenStack、AWS 等云平台。

## 已编译版本

- 0.33 (2026-05-30)

## 特性

- 云镜像分区管理（growpart）
- 创建本地数据源（cloud-localds）
- 云实例元数据查询（ec2metadata）
- 支持多种云平台

## 使用方法

```bash
# 扩展分区
growpart /dev/sda 1
# 创建 cloud-init 数据源
cloud-localds user-data.img user-data.yaml
```