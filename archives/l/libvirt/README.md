# libvirt

libvirt 是一套开源的虚拟化管理 API、守护进程和管理工具集，为多种虚拟化技术提供统一的管理接口。

## 功能概述

libvirt 提供以下核心功能：

- **虚拟机生命周期管理**：创建、启动、停止、暂停、恢复、迁移虚拟机
- **多虚拟化技术支持**：KVM、QEMU、Xen、LXC、VirtualBox 等
- **资源管理**：CPU、内存、存储、网络的分配和监控
- **远程管理**：通过 SSH 或 TCP 连接远程宿主机
- **安全机制**：SELinux、sVirt 等安全集成
- **存储管理**：虚拟磁盘创建、快照、克隆
- **网络管理**：虚拟网络创建、NAT、桥接配置

## OHOS 适配要点

### 编译配置

- 使用 meson 构建系统，需正确配置编译选项
- 主要依赖：glib2、libxml2、readline、ncurses
- 建议禁用不需要的驱动以减少编译依赖

### 已知问题

- virsh 命令行工具可能因配置问题未编译，需检查构建选项
- 部分驱动可能因依赖缺失而禁用

### 与 Linux 的差异

- 系统调用差异：部分 syscall 在 OpenHarmony 未实现
- 文件系统限制：HMDFS 软链接行为与 ext4 不同
- 安全机制：OpenHarmony 的 SELinux 实现与 Linux 有差异

## 依赖关系

### 编译依赖

- glib2：核心工具库
- libxml2：XML 解析库
- readline：命令行编辑库
- ncurses：终端界面库

### 运行依赖

- qemu：虚拟化后端（如使用 QEMU 驱动）
- dnsmasq：网络服务（如使用网络驱动）

## 参考资料

- 官网：https://libvirt.org
- 源码仓库：https://gitlab.com/libvirt/libvirt
- 文档：https://libvirt.org/docs.html
- API 参考：https://libvirt.org/html/