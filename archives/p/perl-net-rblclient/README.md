# perl-net-rblclient

Net::RBLClient — 并行查询多个实时黑名单 (Realtime Blackhole Lists) 的 Perl 模块。

## 简介

Net::RBLClient 用于发现哪些 RBL 列表包含了特定 IP 地址。它通过并行化 DNS 查询实现快速响应。

模块自带 `spamalyze` 工具脚本，可分析 mbox 格式邮件文件，展示不同 RBL 对邮件过滤的影响。

## 版本历史

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 0.5-r8 | built | 2026-06-29 | 纯 Perl 模块，补丁修复 spamalyze 语法错误 |

## 依赖

| 依赖 | 版本 | 类型 |
|------|------|------|
| Perl | 5.42.0 | 运行时 |
| IO::Socket | 1.55 | Perl 核心 |
| Time::HiRes | 1.9778 | Perl 核心 |
| Net::DNS | 1.55 | 运行时（需单独安装） |

## 使用示例

```perl
use Net::RBLClient;

my $rbl = Net::RBLClient->new();
$rbl->lookup('211.101.236.160');
my @listed_by = $rbl->listed_by();
print "Listed by: @listed_by\n";
```

## 鸿蒙平台适配说明

- 纯 Perl 模块，无 XS/C 扩展，不受 SELinux HMDFS 限制
- 使用 `perl Makefile.PL INSTALL_BASE=/` + `make` + `make install DESTDIR` 构建
- 补丁 `0001-fix-spamalyze-syntax-error.patch` 修复了 spamalyze 脚本的语法错误
- Conan 配方通过 G0-G4 + L4/L5 验证，L2 为 Perl 脚本误报
