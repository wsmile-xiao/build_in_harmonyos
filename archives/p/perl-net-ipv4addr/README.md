# perl-net-ipv4addr

Perl extension for manipulating IPv4 addresses.

## 版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 0.10-r7 | built | 2026-06-26 |

## 描述

Net::IPv4Addr 提供了一组用于操作 IPv4 地址的 Perl 函数，包括：

- `ipv4_parse` - 解析 IP 地址/CIDR
- `ipv4_chkip` - 验证 IP 地址合法性
- `ipv4_network` - 计算网络地址
- `ipv4_broadcast` - 计算广播地址
- `ipv4_in_network` - 检查 IP 是否在指定网络内
- `ipv4_dflt_netmask` - 获取默认子网掩码
- `ipv4_cidr2msk` / `ipv4_msk2cidr` - CIDR 与子网掩码互转

还提供 `ipv4calc` 命令行工具用于 IPv4 地址计算。

## 构建系统

ExtUtils::MakeMaker (Makefile.PL) — 纯 Perl 模块，无需 C/C++ 编译。

## 许可证

Artistic-1.0-Perl
