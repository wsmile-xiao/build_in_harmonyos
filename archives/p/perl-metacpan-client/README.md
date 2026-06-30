# perl-metacpan-client (MetaCPAN::Client)

A comprehensive, DWIM-featured client to the MetaCPAN API.

## Versions

| Version | Status | Build Date | Tests |
|---------|--------|------------|-------|
| 2.033000 | built | 2026-06-18 | 261 pass, 0 fail |

## Description

MetaCPAN::Client is a client library for accessing the MetaCPAN API. It provides
a comprehensive interface for searching and retrieving information about CPAN
modules, distributions, authors, releases, and other CPAN metadata.

## Build System

- ExtUtils::MakeMaker (Makefile.PL)
- Pure Perl module (no XS compilation required)
- Dependencies: Moo, Ref::Util, Safe::Isa, Type::Tiny, JSON::MaybeXS

## Test

测试需设置环境变量降级为 HTTP（SSL 不可用）：

```bash
METACPAN_DOMAIN=http://fastapi.metacpan.org make test
```

原因：`Net::SSLeay.so` 安装在 HMDFS 上，SELinux 标签 `hmdfs` 禁止 .so 动态加载，
导致 `IO::Socket::SSL` 失败，HTTPS 全部不可用。`METACPAN_DOMAIN` 环境变量使
MetaCPAN::Client 内置降级为 HTTP，无需修改任何源码。
