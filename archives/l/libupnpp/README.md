# libupnpp

## 简介

libupnpp 是一个用于 UPnP/DLNA 设备的高级 C++ 库，简化了 UPnP 控制点和设备的开发。

## 功能特性

- **高级 UPnP API**: 提供简洁的 C++ 接口，封装底层 UPnP 协议细节
- **媒体渲染器支持**: 支持控制 UPnP/DLNA 媒体渲染器
- **媒体服务器支持**: 支持访问 UPnP 媒体服务器的内容目录
- **OpenHome 扩展**: 支持OpenHome协议扩展，提供更丰富的控制功能
- **多设备管理**: 可同时管理和控制多个 UPnP 设备
- **事件订阅**: 支持 UPnP 事件订阅机制（GENA）
- **SOAP 调用**: 支持远程过程调用（SOAP）

## 编译版本

| 版本 | 状态 | 编译日期 |
|------|------|---------|
| 1.0.4 | built | 2026-06-15 |

## 依赖

- libnpupnp >= 6.3.0
- libcurl >= 8.0.0

## 使用说明

通过 pkg-config 检查安装：

```bash
pkg-config --modversion libupnpp
```

编译链接：

```bash
g++ myapp.cpp $(pkg-config --cflags --libs libupnpp)
```

## 来源

- 官方网站: https://www.lesbonscomptes.com/upmpdcli/
- 源码下载: https://www.lesbonscomptes.com/upmpdcli/downloads/libupnpp-{version}.tar.gz
- 文档: https://www.lesbonscomptes.com/upmpdcli/libupnpp-doc/

## 许可证

BSD-3-Clause License

## 相关软件

- libnpupnp: UPnP 协议栈库
- upmpdcli: UPnP 媒体渲染器接口