# Crypt::OpenSSL::Verify

> OpenSSL X509 证书验证 Perl XS 模块

## 简介

Crypt::OpenSSL::Verify 提供 Perl 接口用于 OpenSSL X509 证书验证。通过 XS (Perl C 扩展) 直接调用 OpenSSL 的 `X509_STORE_CTX` 系列函数，实现证书链验证、CA 加载、证书有效性检查等功能。

上游作者: Timothy Legge (TIMLEGGE), CPAN 发行版 [Crypt-OpenSSL-Verify](https://metacpan.org/dist/Crypt-OpenSSL-Verify)。

## OHOS 适配要点

- **Crypt::OpenSSL::Guess 绕过**: 该配置依赖模块在 OHOS 上不可用，补丁 `0001-Makefile.PL.patch` 内联实现 OpenSSL 版本检测（`openssl version` 命令）和路径解析（`$ENV{OPENSSL_PREFIX}` 环境变量，默认 `/usr/local`）
- **SELinux 限制 (E073)**: 用户编译的 .so 位于 tmpfs，SELinux 上下文为 `hmdfs`，dlopen 被策略阻止。需安装到 `/data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64/` 获取 `hnp_file` 上下文方可运行时加载
- **安全标志**: GNU_STACK=RW (NX 启用), Full RELRO, PIE — conan-verify L4 扫描器报告 "NX=disabled" 为误报

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| OpenSSL | 3.5.6 | 系统预装, 通过 OPENSSL_PREFIX 定位 |
| Perl | 5.42.0 | XS 编译需要 Perl 开发头文件 |
| Crypt::OpenSSL::X509 | 2.1.2 | 运行时依赖 |
| Crypt::OpenSSL::Guess | 0.015 | 配置依赖 (已通过补丁绕过) |

## 功能验证

```bash
# 部署到系统 Perl 目录后验证
sudo cp lib/perl5/aarch64-linux/auto/Crypt/OpenSSL/Verify/Verify.so \
  /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/auto/Crypt/OpenSSL/Verify/
sudo cp lib/perl5/Crypt/OpenSSL/Verify.pm \
  /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/Crypt/OpenSSL/

# 验证模块加载
perl -e 'use Crypt::OpenSSL::Verify; print "OK\n"'
```

## 参考

- [CPAN Crypt-OpenSSL-Verify](https://metacpan.org/dist/Crypt-OpenSSL-Verify)
- [OpenSSL X509 API](https://www.openssl.org/docs/man3.0/man3/X509_STORE_CTX_new.html)
