# perl-socket-getaddrinfo

XS getaddrinfo interface for Perl (Socket::GetAddrInfo).

## 软件信息

- **官网**: https://metacpan.org/pod/Socket::GetAddrInfo
- **源码**: https://cpan.metacpan.org/authors/id/P/PE/PEVANS/Socket-GetAddrInfo-0.22.tar.gz
- **许可证**: Artistic-1.0-Perl
- **分类**: network

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 0.22 | published | 2026-07-02 | conan-verify 全部通过，功能测试通过 |

## 运行依赖

- perl 5.42.0

## 编译依赖

- musl (提供标准 C 库头文件)

## 使用说明

Socket::GetAddrInfo 提供 Perl 接口到系统的 getaddrinfo() 和 getnameinfo() 函数，
支持 IPv4/IPv6 地址解析。

```perl
use Socket qw( SOCK_STREAM );
use Socket::GetAddrInfo qw( getaddrinfo );

my ( $err, @res ) = getaddrinfo( "127.0.0.1", "80", { socktype => SOCK_STREAM } );
die "Cannot resolve name - $err" if $err;
```

### 安装

预编译包安装到 `/data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/` 目录。

### 注意事项

- 由于 SELinux HMDFS 限制，XS 模块需要安装到系统目录 `/data/service/hnp` 才能正常加载
- 原始源码使用 Module::Build 构建，鸿蒙系统不支持，已在 conanfile.py 中重写为 ExtUtils::MakeMaker

---
*OpenHarmony 编译归档 · 2026-07-02*
