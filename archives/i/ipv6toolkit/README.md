# ipv6toolkit

SI6 Networks IPv6 安全评估工具套件，包含 18 个 IPv6 协议分析和安全测试工具。

## 简介

ipv6toolkit 是一套全面的 IPv6 安全评估工具，由 SI6 Networks 开发。该工具套件支持 IPv6 协议的各种安全测试，包括地址扫描、分片攻击、ICMPv6 攻击、路由欺骗等。所有工具依赖 libpcap 进行原始网络数据包操作。

## 包含工具

### 编译工具（16 个 C 程序）
- **addr6** — IPv6 地址分析与转换工具（bin）
- **flow6** — IPv6 流标签操纵工具
- **frag6** — IPv6 分片操纵工具
- **icmp6** — ICMPv6 消息操纵工具
- **jumbo6** — IPv6 超大包（jumbogram）操纵工具
- **mldq6** — MLD 查询工具
- **na6** — IPv6 邻居发现（Neighbor Advertisement）操纵工具
- **ni6** — IPv6 节点信息查询工具
- **ns6** — IPv6 邻居请求（Neighbor Solicitation）操纵工具
- **path6** — IPv6 路径发现工具
- **ra6** — IPv6 路由通告（Router Advertisement）操纵工具
- **rd6** — IPv6 重定向消息操纵工具
- **rs6** — IPv6 路由请求（Router Solicitation）操纵工具
- **scan6** — IPv6 地址扫描工具
- **tcp6** — IPv6 TCP 操纵工具
- **udp6** — IPv6 UDP 操纵工具

### 脚本工具（2 个）
- **blackhole6** — IPv6 黑洞检测工具（Shell 脚本）
- **messi** — IPv6 消息操纵工具（Shell 脚本）
- **script6** — IPv6 脚本自动化工具（Perl 脚本，需要 Net::IP 模块）

## 依赖

- libpcap（网络数据包捕获库）

## 鸿蒙适配说明

- 编译需要添加 `-D__OHOS__` 到 CFLAGS（激活源码中的平台守卫）
- 需要修复 `linux/socket.h` 与 `sys/socket.h` 中 `sockaddr_storage` 重定义问题（补丁已处理）
- 大部分工具需要 superuser 权限运行（raw socket 访问）
- script6 需要额外安装 Perl Net::IP 模块
