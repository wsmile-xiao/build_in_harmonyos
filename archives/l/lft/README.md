# lft

**Layer Four Traceroute (LFT)** — 快速多协议 traceroute 网络诊断工具，利用 TCP SYN/ACK、UDP、ICMP 等协议特性发现网络路径，可绕过防火墙和 ACL 限制。

## 简介

lft 是一款网络诊断工具，追踪数据包通过 IP 网络到达目标主机的路径。与传统 traceroute 不同，lft 使用多种协议（TCP SYN、UDP、ICMP）探测，在受限网络环境中提供更详细、更可靠的结果。

## 主要功能

- 多协议探测（TCP SYN、UDP、ICMP）
- 防火墙/ACL 绕过能力
- AS（自治系统）号查询集成
- Watch 模式（持续监控）
- 基于 libpcap 的数据包捕获

## 编译版本

- **3.93** — 已编译适配 HarmonyOS (OpenHarmony) aarch64 平台
  - 包含 lft (v3.93) 和 whob (v3.92) 两个二进制
  - 依赖: libpcap

## 运行说明

- lft traceroute 功能需要 `CAP_NET_RAW` 权限（root 或特权用户执行）
- 查看版本: `lft -v`（不支持 `--version`）
- whob 查看版本: `whob -v`