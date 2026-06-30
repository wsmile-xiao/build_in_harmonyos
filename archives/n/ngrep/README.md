# ngrep

## 简介

ngrep 是网络层的 grep 工具。它基于 PCAP，允许你指定扩展正则表达式或十六进制表达式来匹配数据包的数据载荷。

## 功能特性

- 支持 IPv4/6, TCP, UDP, ICMPv4/6, IGMP 和 Raw 协议
- 理解 BPF 过滤逻辑（与 tcpdump 和 snoop 相同）
- 支持多种接口类型
- PCRE2 正则表达式支持
- IPv6 支持
- 容器名称解析（Docker/Podman）

## 编译信息

- 版本：1.49.0
- 构建系统：autotools
- 依赖：libpcap, pcre2（静态链接）
- 配置选项：`--enable-pcre2 --enable-ipv6`

## 使用方法

```bash
ngrep -q 'GET|POST' tcp port 80
ngrep -d eth0 'pattern' host 192.168.1.1
```

## 更多信息

- 官方网站：https://ngrep.sourceforge.net/
- GitHub：https://github.com/jpr5/ngrep