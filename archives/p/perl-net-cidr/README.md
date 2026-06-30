# perl-net-cidr

**Net::CIDR** — Manipulate IPv4/IPv6 netblocks in CIDR notation.

纯 Perl 模块，用于处理 IPv4/IPv6 CIDR 表示法的网络地址块。

## 版本历史

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 0.27-r0 | published | 2026-06-25 | 首次适配 OpenHarmony |

## 功能

Net::CIDR 提供以下函数：

- `range2cidr` — 将 IP 范围转换为 CIDR 列表
- `cidr2range` — 将 CIDR 转换为 IP 范围
- `cidr2octets` — 将 CIDR 转换为八位组
- `cidradd` — 合并/扩展 CIDR
- `cidrlookup` — 查找 IP 是否在 CIDR 范围内
- `cidrvalidate` — 验证 CIDR 表示法
- `addr2cidr` — 将地址转换为所有可能的 CIDR
- `addrandmask2cidr` — 将地址和掩码转换为 CIDR

## 使用说明

```perl
use Net::CIDR ':all';

# 转换 IP 范围为 CIDR
my @cidrs = range2cidr("192.168.0.0-192.168.255.255");
# 结果: ("192.168.0.0/16")

# 查找 IP 是否在范围内
my $found = cidrlookup("192.168.1.50", "192.168.1.0/24");
# 结果: true

# 支持 IPv6
my @ipv6 = range2cidr("dead:beef::-dead:beef:ffff:ffff:ffff:ffff:ffff:ffff");
# 结果: ("dead:beef::/32")
```

## 平台兼容性

- **OpenHarmony aarch64**: ✅ 完全兼容
- **纯 Perl 实现**: 无 C/XS 依赖，不受 SELinux/HMDFS 限制
- **性能**: 30,834 ops/s (range2cidr)
