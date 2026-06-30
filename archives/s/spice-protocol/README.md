# spice-protocol

## 简介

spice-protocol 是 SPICE (Simple Protocol for Independent Computing Environments) 项目的协议定义头文件包。它定义了 SPICE 协议的数据结构、消息格式和接口定义，用于：

- spice-server: QEMU 和 x11spice 使用的服务器端库
- spice-gtk: virt-viewer、virt-manager 和 GNOME Boxes 使用的客户端库
- linux/vd-agent 和 win32/vd-agent: Linux 和 Windows 的 Guest 组件
- xf86-video-qxl、gpu/drm/qxl 等: Guest 视频驱动

## 官方网站

- 主页: https://www.spice-space.org
- 源码: https://gitlab.freedesktop.org/spice/spice-protocol

## 版本信息

| 版本 | 发布日期 | 编译状态 |
|------|---------|---------|
| 0.14.5 | 2025-04-30 | published |

## 依赖关系

spice-protocol 是一个纯头文件包，无编译依赖。

## 使用方式

通过 pkg-config 检查安装：
```bash
pkg-config --modversion spice-protocol
pkg-config --cflags spice-protocol
```

头文件安装位置：`$PREFIX/include/spice-1/spice/`

## 许可证

BSD License