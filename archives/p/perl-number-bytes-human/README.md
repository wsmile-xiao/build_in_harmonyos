# perl-number-bytes-human

**Number::Bytes::Human** — 将字节数转换为人类可读格式

## 简介

Number::Bytes::Human 提供了将字节数（如 1073741824）转换为人类可读格式（如 1.0G）的功能。支持 SI（1000 进制）和二进制（1024 进制）两种模式，可自定义精度和舍入方式。

## 版本

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 0.11-r2 | published | 2026-06-29 | 初始鸿蒙平台适配版本 |

## 使用说明

```perl
use Number::Bytes::Human;

# 默认二进制模式 (1024 base)
my $h = Number::Bytes::Human->new();
print $h->format(1073741824);  # 输出: 1.0G

# SI 模式 (1000 base)
my $si = Number::Bytes::Human->new(si => 1);
print $si->format(1500);  # 输出: 1.5KiB

# 反向解析
print $h->parse("1.0G");  # 输出: 1073741824
```

## 鸿蒙平台安装

```bash
# 通过 Conan 安装
conan install --requires=perl-number-bytes-human/0.11-r2

# 或手动设置 PERL5LIB
export PERL5LIB=/path/to/lib:$PERL5LIB
```

## 依赖

- Perl 5.42.0+ (纯 Perl 模块，无需 C 编译器)
- 无其他外部依赖
