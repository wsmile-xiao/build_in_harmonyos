# lldpd

lldpd 是 IEEE 802.1AB 链路层发现协议 (LLDP) 的开源实现，同时兼容 CDP/EDP/SONMP/FDP，
用于在以太网交换机/路由器/网卡之间通告和发现邻居设备信息。

## 版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 1.0.21 | built | 2026-07-15 |

## 描述

lldpd 以守护进程方式监听网络接口，接收并解析对端发来的 LLDP/CDP 等帧，向本机应用
暴露邻居信息。其客户端库 liblldpctl 提供稳定的 C API，用于查询接口、机箱 (chassis)、
端口 (port) 等信息。

## 核心产物

- **lldpd** — 链路层发现协议守护进程（运行需 root 及原始套接字权限）
- **lldpcli** — 命令行客户端，通过 Unix 域套接字与 lldpd 通信
- **liblldpctl** — 客户端 C 库，提供机箱/端口原子 (atom) 编解码与连接管理 API

## 上游

- 主页：https://lldpd.github.io/
- 源码：https://github.com/lldpd/lldpd
- 许可证：ISC
