# Net::Async::XMPP

> Asynchronous support for the Extensible Message Passing Protocol (XMPP) for Perl

## 简介

Net::Async::XMPP 是一个基于 IO::Async 的异步 XMPP 协议实现，提供客户端和服务器端的 XMPP 协议支持。它由 Tom Molesworth 开发，使用 Protocol::XMPP 作为底层协议解析器，通过 IO::Async 实现异步 I/O。

该模块是纯 Perl 实现，不包含任何 C/C++ 编译代码（XS），使用 ExtUtils::MakeMaker 构建系统。

## OHOS 适配要点

1. **纯 Perl 模块，编译无障碍**: Makefile.PL 开箱即用，`perl Makefile.PL && make && make install` 全部通过，无需任何补丁。

2. **SELinux HMDFS 限制**: 运行时依赖链中包含 XS 模块 (Net::SSLeay, XML::LibXML)，这些 `.so` 文件安装在 HMDFS 路径 (`~/usr/local/lib/`) 下时标签为 `hmdfs:s0`，无法被 `hishell_hap` domain 的进程加载。需管理员安装到系统目录 (`/data/service/hnp/`) 获取 `hnp_file:s0` 标签。

3. **CPAN 安装策略**: `cpan` 命令在 OpenHarmony 上会超时。需手动从 `cpan.metacpan.org` 下载 tarball，使用 `fastapi.metacpan.org/v1/module/<Module>` API 获取正确的 author/dist/version 信息构造下载 URL。

## 依赖

| 依赖 | 版本要求 | 说明 |
|------|---------|------|
| Perl | 5.10.1+ | 运行环境 |
| Future | 0.29+ | 异步 Future |
| Future::Utils | 0.29+ | Future 工具 |
| IO::Async | 0.60+ | 异步 I/O 框架 |
| IO::Async::SSL | 0.14+ | SSL 支持 (依赖 Net::SSLeay XS) |
| IO::Async::Resolver::DNS | 0.04+ | DNS 解析 |
| Protocol::XMPP | 0.006+ | XMPP 协议解析 (依赖 XML::LibXML XS) |
| Mixin::Event::Dispatch | 1.000+ | 事件分发 |
| Socket | 2.000+ | Socket 支持 |
| curry | 任意 | 函数式编程辅助 |

## 功能验证

```bash
# 编译安装
perl Makefile.PL PREFIX=/storage/Users/currentUser/usr/local
make -j1
make install

# 验证主模块加载
perl -MNet::Async::XMPP -e 'print $Net::Async::XMPP::VERSION'
# 预期输出: 0.003

# 验证 Server 模块
perl -MNet::Async::XMPP::Server -e 'print "OK"'
# 预期输出: OK

# 注意: Client 和 Protocol 模块需要 XS 依赖安装到系统目录后才能加载
```

## 参考

- [MetaCPAN - Net::Async::XMPP](https://metacpan.org/release/Net-Async-XMPP)
- [CPAN 源码下载](https://cpan.metacpan.org/authors/id/T/TE/TEAM/Net-Async-XMPP-0.003.tar.gz)