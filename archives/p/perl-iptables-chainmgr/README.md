# perl-iptables-chainmgr

Perl 模块：管理 iptables 防火墙链和规则。

## 描述

IPTables::ChainMgr 是一个纯 Perl 模块，用于管理 iptables 防火墙链和规则。它提供了创建、删除、修改 iptables 链和规则的接口，可与 IPTables::Parse 模块配合使用。

## 版本信息

- 当前版本：1.6
- CPAN 版本：1.6
- 发布日期：2016-12-05

## 构建系统

- 构建系统类型：perl (Makefile.PL)
- 模块类型：pure（纯 Perl，无 XS 代码）
- 无需编译器

## 依赖

- perl 5.42.0（预装）
- IPTables::Parse >= 1.6.1
- NetAddr::IP >= 4.079

## 编译状态

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 1.6 | published | 2026-06-12 | 功能测试通过，依赖已安装 |

## 安装说明

通过 cmd-pkgs 公共安装脚本安装：

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- perl-iptables-chainmgr 1.6
```

安装后验证：

```perl
use IPTables::ChainMgr;
print $IPTables::ChainMgr::VERSION;
```

**注意**：需要先安装依赖模块：
- perl-iptables-parse 1.6.1-r4
- perl-netaddr-ip 4.079

## 功能特性

- 创建和删除 iptables 链
- 添加、删除、修改规则
- 支持各种 iptables 目标（ACCEPT、DROP、LOG 等）
- 支持规则匹配条件（源地址、目标地址、端口等）
- 纯 Perl 实现，无平台依赖

## 使用示例

```perl
use IPTables::ChainMgr;

my $ipt = IPTables::ChainMgr->new(
    'iptables' => '/usr/bin/iptables',
    'iptables_restore' => '/usr/bin/iptables-restore',
    'iptables_save' => '/usr/bin/iptables-save',
);

# 创建新链
$ipt->create_chain('filter', 'MYCHAIN');

# 添加规则
$ipt->add_rule('filter', 'INPUT', 'MYCHAIN', 1);
```

## 注意事项

1. **PERL5LIB 配置**：需要设置环境变量才能加载模块：
   ```bash
   export PERL5LIB="/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0:$PERL5LIB"
   ```
2. **纯 Perl 模块**：无 XS 代码，编译简单。
3. **依赖顺序**：需先安装 IPTables::Parse 和 NetAddr::IP。

## 许可证

与 Perl 相同的开源许可证（Perl Artistic License 或 GPL）。

Copyright (C) 2005-2016 by Michael Rash

## 来源

- CPAN: https://cpan.metacpan.org/authors/id/M/MR/MRASH/IPTables-ChainMgr-1.6.tar.gz
- 原项目: https://www.cipherdyne.org/blog/