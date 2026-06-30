# apt-dater-host

## 简介

apt-dater-host 是一个终端远程包更新管理器的主机端实现，支持 ADP（apt-dater protocol）协议 0.6 版本。它为 apt-dater 客户端提供主机端接口，用于查询和管理远程系统的软件包状态。

## 功能特性

- 提供系统信息查询（LSBREL、KERNELINFO、VIRT）
- 提供软件包状态查询（STATUS、PRL）
- 支持虚拟化环境检测
- 通过 sudo 实现权限提升
- 基于 Busybox ash/awk/sed 实现（适用于 Alpine Linux）

## 技术特点

- 纯 shell 脚本实现，无需编译
- 依赖 Busybox 工具链（ash、awk、sed）
- 支持 ADP 协议版本 0.6
- 轻量级设计，适合嵌入式系统

## 使用场景

- 配合 apt-dater 客户端进行远程包管理
- 用于 OpenHarmony 系统的包状态监控
- 集成到自动化运维系统中

## 许可证

GNU General Public License v2.0 或更高版本

## 作者

Henrik Riomar <henrik.riomar@gmail.com>

## 参考资料

- [ADP 协议文档](https://github.com/DE-IBH/apt-dater-host/blob/master/doc/ADP-0.6)
- [apt-dater-host 项目](https://github.com/DE-IBH/apt-dater-host)