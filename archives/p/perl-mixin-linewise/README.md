# perl-mixin-linewise

Mixin::Linewise - write your linewise code for handles; this does the rest

## 描述

Mixin::Linewise 提供了 Mixin::Linewise::Readers 和 Mixin::Linewise::Writers 两个模块，
用于简化面向行的文件/字符串 I/O 操作。

- **Mixin::Linewise::Writers**: 纯 Perl 实现，完全可用
- **Mixin::Linewise::Readers**: 依赖 PerlIO::utf8_strict XS 模块

## 版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 0.111 | built | 2026-06-18 |

## 依赖

- Sub::Exporter >= 0.987（纯 Perl）
- PerlIO::utf8_strict >= 0.010（XS，需 HNP 安装）

## 平台注意事项

Readers 模块依赖的 PerlIO::utf8_strict XS 模块因 SELinux HMDFS 限制无法从 `~/usr/local` 加载。
管理员需安装 HNP 包到 `/data/service/hnp/perl.org/perl_5.42.0/`。
