# perl-socket

Perl Socket 模块 — 网络常量和地址操作函数 (Perl XS 模块)。

## 软件信息

- **官网**: https://metacpan.org/dist/Socket
- **源码**: https://cpan.metacpan.org/authors/id/P/PE/PEVANS/Socket-2.040.tar.gz
- **许可证**: Artistic-1.0-Perl
- **分类**: network / perl

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 2.040-r0 | published | 2026-07-01 | 修复 test_package Conan API bug，新增 ELF 验证，功能测试通过 |

## 运行依赖

- perl (系统自带 5.42.0)

## 使用说明

Socket 模块提供网络编程所需的常量和函数，包括：

- 地址族常量: AF_INET, AF_INET6, AF_UNIX
- 套接字类型: SOCK_STREAM, SOCK_DGRAM, SOCK_RAW
- 地址转换: inet_aton, inet_ntoa, inet_pton, inet_ntop
- 地址打包/解包: pack_sockaddr_in, unpack_sockaddr_in, pack_sockaddr_in6, unpack_sockaddr_in6
- Unix 域套接字: pack_sockaddr_un, unpack_sockaddr_un
- 名称解析: getaddrinfo, getnameinfo
- 多播: pack_ip_mreq, pack_ipv6_mreq

### 安装

```bash
# 通过 Conan 安装
conan install --requires=perl-socket/2.040-r0

# 或手动安装到系统目录
cp lib/Socket.pm /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/
cp lib/auto/Socket/Socket.so /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/auto/Socket/
```

### 注意事项

- 鸿蒙 SELinux HMDFS 限制：动态库 (.so) 必须安装到 `/data/service/hnp/` 系统目录才能被 Perl 加载
- 系统自带 Socket 2.038，本包为 CPAN 最新版 2.040，两者导出符号完全一致
- 无需源码补丁，`perl Makefile.PL` 自动处理平台差异

---

*OpenHarmony 编译归档 · 2026-07-01*
