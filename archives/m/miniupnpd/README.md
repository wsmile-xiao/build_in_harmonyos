# miniupnpd

miniupnpd 是 MiniUPnP 项目里的 UPnP IGD（Internet Gateway Device）守护进程：
在网关上监听 SSDP 组播（239.255.255.250:1900）宣告自己，接受控制点的
AddPortMapping/DeletePortMapping 请求，并把端口映射下发到本机防火墙；
同时实现 NAT-PMP 与 PCP（Port Control Protocol）两个自动端口映射协议。

## 功能概述

- UPnP IGD v1 / v2（`--igd2`）设备与服务，含 WANIPConnection、WANPPPConnection、
  Layer3Forwarding、WANIPv6FirewallControl 等 SCPD 描述
- SSDP 发现：组播监听 + NOTIFY/M-SEARCH 应答，支持 IPv6（`--ipv6`）
- NAT-PMP / PCP 服务端（`ENABLE_NATPMP` / `ENABLE_PCP`，默认开启）
- 防火墙后端：iptables、nftables（Linux），pf/ipf/ipfw（BSD）
- HTTP 控制端口（默认 5000）、可选 HTTPS（IGDv2，`--https`）、STUN 外网地址探测
- `miniupnpdctl` 调试客户端（需编译期打开 `USE_MINIUPNPDCTL`）

## OHOS 适配

- **构建入口**：上游手写 `configure` + `Makefile.linux_nft`（无 autoconf）。
  `uname -s` 在鸿蒙上是 `HarmonyOS`，上游 OS 分支不识别 → 走其自带的
  交叉分支 `--host-os=Linux --host-os-version=1.12.0 --host-machine=aarch64`。
- **防火墙后端**：iptables 后端需要 `<xtables.h>` 与 `<libiptc/libiptc.h>`
  （来自 iptables 源码树），制品仓无对应配方 → 选 nftables 后端，
  依赖 `libnftnl/1.3.1` + `libmnl/1.0.5`（ohpcd 有 armv8/clang15 预编译）。
- **头文件冲突**：OHOS SDK 的 `<linux/socket.h>` 会与 `<sys/socket.h>` 重复
  定义 `struct sockaddr_storage` → `CPPFLAGS` 追加
  `-D_UAPI_LINUX_SOCKET_H -D__kernel_sa_family_t=sa_family_t`（与 libnftnl 同款）。
- **测试工具**：上游 `testgetifaddr.sh` 用 `command -v ip` 探测 iproute2；
  鸿蒙 toybox 未编入 `ip` applet，由 busybox 提供（配方在构建时把它挂到 PATH，
  不修改上游测试脚本）。
- **运行时能力**：`test_package/ohos_netprobe.c` 实测——无特权进程可用
  UDP/组播加入与环回收发、rtnetlink（RTM_GETLINK / RTM_GETROUTE）、
  netlink RTMGRP_LINK 订阅、`SIOCGIFADDR/FLAGS/MTU/NETMASK`、`getifaddrs()`、
  `/proc/net/dev`；`NETLINK_NETFILTER`、`AF_PACKET`、raw socket、
  `/proc/sys/kernel/random/uuid` 需要相应 capability（无特权返回 EACCES），
  因此 nftables 规则下发与 `genuuid` 回退路径在无特权下不可用——
  与所有防火墙类守护一样，miniupnpd 的映射下发需要 root/管理员权限。

## 依赖关系

- 编译依赖：`libnftnl/1.3.1`（自带 `libmnl/1.0.5` 传递依赖）
- 运行依赖：无（静态链接；防火墙工具 `nft` 由系统提供，仅在下发规则时需要）

## 参考资料

- 上游项目：https://miniupnp.tuxfamily.org/
- 上游仓库：https://github.com/miniupnp/miniupnp
- UPnP Device Architecture：https://upnp.org/resources/documents/UPnPDA-1_1.pdf
