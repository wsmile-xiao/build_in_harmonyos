# perl-net-cidr-lite

Perl extension for merging IPv4 or IPv6 CIDR addresses.

## 描述

Net::CIDR::Lite 是一个轻量级的 Perl 模块，用于合并和管理 IPv4/IPv6 CIDR 地址范围。与传统 Net::CIDR 模块相比，它使用更高效的内部数据结构（基于范围标记的哈希），在处理大量 CIDR 地址时性能更好。

## 版本历史

| 版本 | 日期 | 状态 | 说明 |
|------|------|------|------|
| 0.23-r0 | 2026-06-25 | built | 纯 Perl 模块，OpenHarmony aarch64 平台编译通过 |

## 主要功能

- IPv4/IPv6 CIDR 地址合并
- IP 范围添加与查找
- CIDR 列表与范围列表输出
- 地址查找（判断 IP 是否在范围内）
- 支持 `add`、`add_any`、`add_ip`、`add_range`、`add_cidr` 等多种添加方式
- `clean` 方法合并重叠范围
- `list`、`list_range`、`list_short_range` 多种输出格式
- `find` 方法快速地址查找
- `Net::CIDR::Lite::spanner` 子类支持 CIDR 跨度计算

## 构建系统

- **类型**: Perl Makefile.PL (ExtUtils::MakeMaker)
- **编译器**: 不需要（纯 Perl 模块）
- **依赖**: 无

## 使用说明

```perl
use Net::CIDR::Lite;

# 创建实例
my $cidr = Net::CIDR::Lite->new;

# 添加 CIDR
$cidr->add("192.168.0.0/24");
$cidr->add("192.168.1.0/24");

# 获取合并后的列表
my @list = $cidr->list;
# 返回: ("192.168.0.0/23")

# 查找 IP
if ($cidr->find("192.168.0.100")) {
    print "IP in range\n";
}

# 添加多种格式
$cidr->add_any("10.0.0.0/8");        # CIDR
$cidr->add_any("172.16.0.0-172.16.255.255");  # 范围
$cidr->add_any("192.168.1.1");       # 单个 IP
```

## OpenHarmony 平台信息

- **平台**: OpenHarmony (aarch64-unknown-linux-ohos)
- **Perl 版本**: 5.42.0
- **安装路径**: `~/usr/local/lib/site_perl/5.42.0/Net/CIDR/Lite.pm`
- **平台兼容性**: ✅ 完全兼容（纯 Perl 模块，无 XS/C 依赖）
