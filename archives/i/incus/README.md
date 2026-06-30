# incus

Incus 是 LXD 项目的社区分支，提供强大的系统容器和虚拟机管理功能。

## 描述
Incus 是从 Canonical LXD 项目 fork 出来的社区版本，专注于开放治理和社区驱动。支持系统容器（LXC）和虚拟机管理，提供 REST API 和命令行工具。

## 已编译版本
- 7.1.0 (2026-06-17)

## 依赖
- Go 1.26.0

## 特性
- 系统容器（LXC）管理
- 虚拟机管理（QEMU）
- REST API 支持
- 远程镜像仓库
- 存储池管理
- 网络配置
- 项目隔离

## 使用方法
```bash
# 列出容器
incus list

# 启动容器
incus launch ubuntu:22.04 my-container

# 进入容器
incus exec my-container -- bash

# 管理虚拟机
incus launch ubuntu:22.04 my-vm --vm
```

## 注意事项
- CGO_ENABLED=0 编译，仅编译客户端工具（incus, incus-migrate, incus-simplestreams, incus-user）
- incusd 等服务端组件需要 CGO + liblxc，无法在鸿蒙上编译
- 无需源码修改，无补丁文件
