# lxc-templates-legacy

LXC 容器模板脚本集 - 传统版本

## 描述

lxc-templates-legacy 提供用于创建各种 Linux 发行版 LXC 容器的模板脚本集合。包含 21 个模板脚本，支持 Alpine、Arch Linux、CentOS、Debian、Fedora、Gentoo、OpenSUSE、Oracle、Ubuntu、Void Linux 等发行版。

## 编译版本

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| 3.0.4 | built | 2026-05-27 |

## 功能特点

- 21 个模板脚本覆盖主流 Linux 发行版
- 34 个配置文件支持各种容器配置选项
- 支持 rootless 容器（userns.conf 配置）
- 需要配合 LXC 工具链使用

## 依赖

- gnupg (镜像签名验证)
- debootstrap (Debian/Ubuntu 模板)

## 使用方法

```bash
# 创建 Alpine 容器
lxc-create -n alpine-container -t alpine

# 创建 Debian 容器  
lxc-create -n debian-container -t debian

# 创建 Ubuntu 容器
lxc-create -n ubuntu-container -t ubuntu
```

## 注意事项

- 模板脚本需要 root 权限执行
- 需要 LXC 工具链已安装
- Debian/Ubuntu 模板需要 debootstrap
- 部分模板需要网络下载发行版镜像
