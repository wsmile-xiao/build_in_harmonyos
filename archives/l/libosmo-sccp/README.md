# libosmo-sccp

## 简介

libosmo-sccp 是 Osmocom 项目族的 SCCP/SIGTRAN 协议栈实现，提供 SCCP
（Signalling Connection Control Part）、M3UA、SUA、xUA、IPA 与
SS7（Signalling System No. 7）应用服务器进程（ASP）/应用服务器（AS）
框架，以及 **osmo-stp** 信号转接点（STP）守护进程。

## 主要功能

- libosmo-sigtran.so：SCCP / M3UA / SUA / xUA / IPA 协议栈主库
- libsccp.a / libmtp.a / libxua.a：legacy 静态库
- osmo-stp：信号转接点（STP）可执行程序
- include/osmocom/{sccp,sigtran,mtp}/ 公共头

## 版本信息

- 当前编译版本：1.9.0
- 许可证：GPL-2.0-or-later

## 依赖

- libosmocore/1.11.0（含 osmocore/osmovty/osmogsm）
- libosmo-netif/1.6.0

## 编译选项

- `--disable-libsctp`：平台无 SCTP（内核 EPROTONOSUPPORT，libosmocore/netif 同源结论）
- `--disable-doxygen`：无 doxygen 工具

## 归档版本
