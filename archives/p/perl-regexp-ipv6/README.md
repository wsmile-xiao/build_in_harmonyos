# perl-regexp-ipv6

Perl regular expression for IPv6 addresses (Regexp::IPv6).

## 软件信息

- **官网**: https://metacpan.org/dist/Regexp-IPv6
- **源码**: https://cpan.metacpan.org/authors/id/S/SA/SALVA/Regexp-IPv6-0.03.tar.gz
- **许可证**: Artistic-1.0-Perl OR GPL-1.0-or-later
- **分类**: perl-module

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 0.03 | published | 2026-06-29 | 纯 Perl 模块，无需特殊适配。198 测试全通过 |

## 运行依赖

- perl 5.42.0

## 编译依赖

无额外依赖（纯 Perl 模块）

## 使用说明

Regexp::IPv6 提供一个匹配 IPv6 地址的正则表达式 `$IPv6_re`，可用于验证和提取 IPv6 地址。

### 安装

通过 Conan 安装：

```bash
conan install --requires=perl-regexp-ipv6/0.03
```

模块安装到 `lib/perl5/Regexp/IPv6.pm`，通过 `PERL5LIB` 环境变量自动加载。

### 示例

```perl
use Regexp::IPv6 qw($IPv6_re);

if ('2001:db8::1' =~ /^$IPv6_re$/) {
    print "Valid IPv6 address\n";
}
```

### 注意事项

- 此模块为纯 Perl 实现，不包含 XS 代码，无需 ELF 签名
- 无平台特殊限制，可在鸿蒙系统正常使用

---
*OpenHarmony 编译归档 · 2026-06-29*
