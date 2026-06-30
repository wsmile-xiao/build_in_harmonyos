# perl-netaddr-ip

Perl 模块：IPv4 和 IPv6 地址及子网管理。

## 描述

NetAddr::IP 是一个 Perl 模块，用于管理 IPv4 和 IPv6 地址和子网。它提供了完整的 IP 地址操作功能，包括地址计算、子网划分、范围检查等。

## 版本信息

- 当前版本：4.079
- CPAN 版本：4.079
- 发布日期：2016-03-26

## 构建系统

- 构建系统类型：perl (Makefile.PL)
- 模块类型：pure (纯 Perl 模式，使用 -noxs 参数)
- 无需编译器

## 依赖

- perl 5.42.0 (预装)
- Socket6 模块 (需要支持 getipnodebyname)

## 编译状态

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 4.079 | built | 2026-06-12 | 纯 Perl 模式编译，测试通过 |

## 安装说明

通过 cmd-pkgs 公共安装脚本安装：

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- perl-netaddr-ip 4.079
```

安装后验证：

```perl
perl -MNetAddr::IP -e 'print $NetAddr::IP::VERSION;'
```

## 功能特性

- IPv4 和 IPv6 地址对象创建和管理
- 子网计算和网络地址识别
- 地址范围检查和包含判断
- CIDR 格式支持
- 纯 Perl 实现，无平台依赖

## 使用示例

```perl
use NetAddr::IP;

# 创建 IP 地址对象
my $ip = NetAddr::IP->new("192.168.1.1/24");
print "Network: ", $ip->network, "\n";
print "Mask: ", $ip->mask, "\n";
```

## 注意事项

1. **Socket6 依赖**：需要 Socket6 模块支持 `getipnodebyname` 函数。当前系统使用兼容包装器实现此函数。
2. **纯 Perl 模式**：使用 `-noxs` 参数编译，无 C 扩展代码。
3. **PERL5LIB 设置**：需要设置环境变量加载模块：
   ```bash
   export PERL5LIB="/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0:$PERL5LIB"
   ```

## 许可证

未知许可证（CPAN metadata 中标记为 unknown）

## 来源

- CPAN: https://cpan.metacpan.org/authors/id/M/MI/MIKER/NetAddr-IP-4.079.tar.gz