# perl-iptables-parse

Perl 模块：解析 iptables 防火墙规则。

## 描述

IPTables::Parse 是一个纯 Perl 模块，用于解析 iptables 防火墙规则配置。它可以读取 iptables 规则列表并提供结构化的数据访问接口。

## 版本信息

- 当前版本：1.6.1-r4
- CPAN 版本：1.6.1
- 发布日期：2015-11-19

## 构建系统

- 构建系统类型：perl（Makefile.PL）
- 模块类型：pure（纯 Perl，无 XS 代码）
- 无需编译器

## 依赖

- perl 5.42.0（预装）
- ExtUtils::MakeMaker（Perl 核心模块）

## 编译状态

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 1.6.1-r4 | built | 2026-06-11 | 纯 Perl 模块，测试通过 |

## 安装说明

通过 cmd-pkgs 公共安装脚本安装：

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- perl-iptables-parse 1.6.1-r4
```

安装后验证：

```perl
perl -MIPTables::Parse -e 'print $IPTables::Parse::VERSION;'
```

## 功能特性

- 解析 iptables-save 格式的规则
- 支持 IPv4 和 IPv6 规则
- 提供链、规则、目标等信息的结构化访问
- 纯 Perl 实现，无平台依赖

## 许可证

与 Perl 相同的开源许可证（Perl Artistic License 或 GPL）。

Copyright (C) 2005-2015 by Michael Rash

## 来源

- CPAN: https://cpan.metacpan.org/authors/id/M/MR/MRASH/IPTables-Parse-1.6.1.tar.gz
- 原项目: https://www.cipherdyne.org/blog/