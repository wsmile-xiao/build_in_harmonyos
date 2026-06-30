# perl-io-socket-inet6

IO::Socket::INET6 - IPv6 socket support for Perl

## 描述

IO::Socket::INET6 是 Perl 的 IPv6 socket 模块，提供 AF_INET/AF_INET6 域 socket 的对象接口。

## 版本

- 2.73-r2 (2026-06-12) - 已发布

## 依赖

- Perl 5.42.0+
- Socket 模块（Perl 内置，提供 IPv6 支持）

## 注意事项

此软件使用内置 Socket 模块的 IPv6 支持，通过 Socket6 兼容层实现，无需安装外部 Socket6 模块。