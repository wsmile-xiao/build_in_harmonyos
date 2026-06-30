# IO-Socket-IP

## 简介

IO::Socket::IP - IPv4/IPv6 协议无关的套接字模块，用于 Perl。

该模块提供了一个协议无关的接口，用于创建 IPv4 和 IPv6 套接字。它是 IO::Socket::INET 的现代替代品，支持 IPv6 和其他高级特性。

## 版本信息

- 当前版本: 0.43
- 发布日期: 2023-12-15
- 源码: https://metacpan.org/release/PEVANS/IO-Socket-IP-0.43

## 依赖关系

### 构建依赖
- Module::Build >= 0.42
- Perl >= 5.42.0

### 运行时依赖
- Perl >= 5.42.0
- IO::Socket（系统内置）

## 特性

- 纯 Perl 模块，无需 XS 编译
- 支持 IPv4 和 IPv6
- 协议无关的 API
- 与 IO::Socket::INET 兼容

## 平台支持

- OpenHarmony aarch64-unknown-linux-ohos
- Linux x86_64
- macOS
- Windows

## 使用方法

```perl
use IO::Socket::IP;

# 创建 TCP 客户端
my $socket = IO::Socket::IP->new(
    PeerHost => 'example.com',
    PeerPort => 'http(80)',
    Type     => SOCK_STREAM,
) or die "Cannot connect: $!";

# 创建 TCP 服务器
my $server = IO::Socket::IP->new(
    LocalHost => '0.0.0.0',
    LocalPort => 8080,
    Listen    => 5,
    Type      => SOCK_STREAM,
    Reuse     => 1,
) or die "Cannot bind: $!";

# 支持 IPv6
my $ipv6_socket = IO::Socket::IP->new(
    PeerHost => '2001:db8::1',
    PeerPort => 80,
);
```

## 编译状态

| 版本 | 状态 | 日期 |
|------|------|------|
| 0.43 | ✅ published | 2026-06-11 |

## 注意事项

1. 纯 Perl 模块，无需编译二进制文件
2. 依赖系统内置的 IO::Socket（包含 XS 扩展）
3. 不要设置 PERL5LIB 环境变量，否则可能导致 XS 模块加载冲突