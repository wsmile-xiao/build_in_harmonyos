# pimd — PIM-SM 组播路由守护进程

`pimd` 是一个独立的 PIM-SM（Protocol Independent Multicast - Sparse Mode）组播
路由守护进程，源自 mrouted 生态。它作为用户态守护进程接收并处理 PIM/IGMP 协议
报文，通过 `/proc`、netlink 或路由 socket 与内核的组播转发表配合工作。

## 主要功能

- 实现 PIM-SM（含 IGMP/IGMPv2/IGMPv3、DVMRP 报文解析）。
- 通过 `pimd.conf` 配置物理接口（phyint）、汇聚点（RP）等。
- 以 root 运行，前台/后台模式，支持日志级别、调试子系统等选项。

## OHOS 适配要点

- **手写 configure**：非 autoconf；补丁加 `HarmonyOS` 分支（等同 Linux），并把
  `mktemp /tmp/XXXXXX` 改成在构建目录建临时文件（OHOS `/tmp` 只读）。
- **零三方依赖、零补丁除上述 configure 两处**：自带 libite 的 strlcpy/strlcat/
  pidfile/strtonum 直接编入 `pimd`。
- 功能级运行需要组播网卡与 root。

## 产物

| 路径 | 说明 |
|------|------|
| `bin/pimd` | PIM-SM 组播路由守护进程 |
| `share/man/man8/pimd.8` | 手册 |
| `share/pimd/pimd.conf` | 示例配置 |

## 参考资料

- 上游仓库：<https://github.com/troglobit/pimd>
- 许可证：BSD-3-Clause
