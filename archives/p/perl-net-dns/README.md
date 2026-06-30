# perl-net-dns

**Net::DNS** — Perl Interface to the Domain Name System.

纯 Perl 模块，提供 DNS 协议的完整实现，支持 DNS 查询、响应解析、动态更新等功能。

## 版本历史

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 1.53-r0 | published | 2026-06-25 | 首次适配 OpenHarmony |

## 功能

Net::DNS 提供以下核心功能：

- **DNS 查询** — 支持所有标准 DNS 记录类型 (A, AAAA, MX, NS, SOA, TXT, SRV 等)
- **DNS 响应解析** — 解析 DNS 报文为 Perl 对象
- **动态更新** — 支持 DNS 动态更新 (RFC 2136)
- **DNSSEC** — 支持 DNSSEC 扩展 (需配合 Net::DNS::SEC)
- **区域传送** — 支持 AXFR/IXFR 区域传送
- **并行查询** — 支持多域名并行查询

## 使用说明

```perl
use Net::DNS;

my $resolver = Net::DNS::Resolver->new();

# 查询 A 记录
my $reply = $resolver->query("example.com", "A");
if ($reply) {
    foreach my $rr ($reply->answer) {
        print $rr->address, "\n" if $rr->type eq "A";
    }
}

# 查询 MX 记录
my $mx = $resolver->query("example.com", "MX");
if ($mx) {
    foreach my $rr ($mx->answer) {
        print $rr->exchange, " (priority ", $rr->preference, ")\n";
    }
}
```

## 平台兼容性

- **OpenHarmony aarch64**: ✅ 完全兼容
- **纯 Perl 实现**: 无 C/XS 依赖，不受 SELinux/HMDFS 限制
