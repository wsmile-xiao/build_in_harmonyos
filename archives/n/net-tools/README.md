# net-tools

Linux 经典 NET-3 网络工具集：`ifconfig` / `route` / `netstat` / `arp` / `rarp` / `hostname` / `nameif` / `iptunnel` / `ipmaddr` / `mii-tool` / `plipconfig` / `slattach`。

## 功能概述

| 工具 | 安装位置 | 职责 |
|---|---|---|
| ifconfig / netstat / route / hostname | bin/ | 接口配置 / 网络状态统计 / 路由表 / 主机名 |
| arp / rarp | sbin/ | ARP 表管理 / 反向 ARP |
| nameif / iptunnel / ipmaddr | sbin/ | 网卡命名 / IP 隧道 / 组播地址 |
| mii-tool / plipconfig / slattach | sbin/ | MII 状态 / PLIP 配置 / SLIP 串行附着 |

## OHOS 适配

- 构建体系：裸 Makefile + `configure.sh config.in`（非 autotools），以 `yes ""` 非交互接受裁剪后的默认值生成 `config.h`。
- 3 个 portability 补丁：config.in 默认值裁剪（禁用 OHOS musl sysroot 缺头文件/库的 IPX/ATALK/AX25 等协议族与 ARC/IrDA 等硬件类型）；`index()/rindex()` → `strchr()/strrchr()`（musl `<strings.h>` 未声明 rindex）。
- `CPPFLAGS=-D__MUSL__`：OHOS musl `<sys/socket.h>` 仅在 `__MUSL__` 下定义 `sockaddr_storage`。
- 消费者测试在真机实跑核心工具查询（`ifconfig -a` / `netstat -rn` / `route -n` / `hostname` / `arp -n`）。

## 依赖关系

无（纯 libc）。

## 参考资料

- 上游项目：https://net-tools.sourceforge.net/
- 上游发布 tarball：`net-tools-2.10.tar.xz`（sha256 `b262435a5241e89bfa51c3cabd5133753952f7a7b7b93f32e08cb9d96f580d69`）
