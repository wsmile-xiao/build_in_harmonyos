# iproute2

iproute2 是 Linux 下用于网络配置、流量控制与网络诊断的核心工具集，包含 `ip`、`tc`、`bridge`、`ss` 等命令，是 net-tools（ifconfig/route/netstat）的现代替代品。

## 功能概述
- `ip` — 网络接口、地址、路由、隧道、邻居表等配置
- `tc` — 流量控制（QoS、队列规则、过滤器）
- `bridge` — 二层桥接与 VLAN 管理
- `ss` — socket 统计（替代 netstat）
- `lnstat` / `nstat` / `rtacct` — 网络统计
- `genl` — generic netlink 工具

## OHOS 适配
- **静态编译（R26）**：命令行工具以 `LDFLAGS=-static` 静态链接。
- **getpass（E215）**：OHOS musl 的 `libc.so` 未导出 `getpass`，但静态 `libc.a` 提供真实现；补声明 + 静态链接即可使用 libc 自带的真 getpass（关闭回显、安全）。
- **内核 UAPI 结构体重定义（E216）**：内核 UAPI 头与 musl `netinet/in.h` 对 `in6_addr`/`sockaddr_in6`/`ipv6_mreq` 重复定义，用 `-D__UAPI_DEF_*=0` 让内核头让位并先包含 `<netinet/in.h>`。

### 适配范围
| 工具 | 状态 |
|------|------|
| ip / tc / bridge / ss / lnstat / nstat / rtacct / genl | ✅ 完整可适配（aarch64 静态） |
| tipc / devlink / rdma / dcb | ⏳ 依赖 libmnl（OHOS sysroot 未含），待 libmnl 先适配 |

## 依赖关系
- 编译依赖：bison、flex（构建时工具）
- 核心工具集无第三方运行依赖
- 可选工具（tipc/devlink/rdma/dcb）依赖 libmnl

## 参考资料
- 官网：https://wiki.linuxfoundation.org/networking/iproute2
- 源码：https://www.kernel.org/pub/linux/utils/net/iproute2/
