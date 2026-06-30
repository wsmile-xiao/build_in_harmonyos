# perl-net-dns-resolver-programmable

**Net::DNS::Resolver::Programmable** — Programmable DNS resolver class for offline emulation of DNS.

纯 Perl 模块，提供可编程的 DNS 解析器类，用于离线模拟 DNS 查询响应。

## 版本历史

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 0.009-r4 | published | 2026-06-25 | 首次适配 OpenHarmony |

## 功能

Net::DNS::Resolver::Programmable 提供以下能力：

- 可编程的 DNS 解析器，允许预设 DNS 响应
- 支持离线模拟 DNS 查询
- 用于测试和开发场景中模拟 DNS 行为
- 基于 Net::DNS 框架，兼容标准 DNS 协议

## 使用说明

```perl
use Net::DNS::Resolver::Programmable;

# 创建可编程解析器实例
my $resolver = Net::DNS::Resolver::Programmable->new();

# 预设 DNS 响应记录
$resolver->records([
    { type => 'A', name => 'example.com', address => '192.0.2.1' },
]);

# 执行查询（返回预设响应）
my $packet = $resolver->query('example.com', 'A');
```

## 平台兼容性

- **OpenHarmony aarch64**: ✅ 完全兼容
- **纯 Perl 实现**: 无 C/XS 依赖，不受 SELinux/HMDFS 限制
- **运行时依赖**: 需要 Net::DNS 模块

## 许可证

Perl 5 (Artistic License 1.0 或 GPL v1+)
