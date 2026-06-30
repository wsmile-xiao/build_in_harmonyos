# perl-ldap

perl-ldap (Net::LDAP) 是一个 Perl 模块集合，提供 LDAP (Lightweight Directory Access Protocol) 客户端功能。

## 描述

Net::LDAP 是一个纯 Perl 实现的 LDAP 客户端库，支持：
- 标准 LDAP 操作（bind, search, add, modify, delete）
- LDAP over SSL/TLS (Net::LDAPS)
- Unix socket LDAP (Net::LDAPI)
- LDAP 控制和扩展
- ASN.1 编解码

## 版本信息

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| 0.68-r2 | published | 2026-06-13 |

## 特性

- ✅ 纯 Perl 模块，无 C/XS 代码
- ✅ 支持 LDAPv3 协议
- ✅ SSL/TLS 加密连接支持
- ✅ Unix socket 连接支持
- ✅ 完整的 ASN.1 编解码

## 依赖

- Convert::ASN1 ≥ 0.34（必需）
- MIME::Base64（随 Perl 核心）
- IO::Socket::SSL（可选，用于 LDAPS）

## 使用说明

### 环境配置

```bash
export PERL5LIB="/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0:/storage/Users/currentUser/usr/local/lib/perl5"
```

### 示例代码

```perl
use Net::LDAP;

# 连接 LDAP 服务器
my $ldap = Net::LDAP->new('ldap.example.com') or die "Cannot connect";

# 绑定认证
$ldap->bind('cn=admin,dc=example,dc=com', password => 'secret');

# 搜索
my $result = $ldap->search(
    base   => 'dc=example,dc=com',
    filter => '(cn=test)'
);

# 处理结果
foreach my $entry ($result->entries) {
    print $entry->dn(), "\n";
}

# 断开连接
$ldap->unbind();
```

## 鸿蒙平台适配

### 编译特点

1. 纯 Perl 模块，使用 `perl Makefile.PL PREFIX=...` 配置
2. 无需特殊编译参数或补丁
3. PERL5LIB 必须指向 site_perl 和 lib/perl5 两个目录

### 已验证功能

| 功能 | 状态 |
|------|------|
| 模块加载 | ✅ |
| Entry 操作 | ✅ |
| Filter 解析 | ✅ |
| LDAPS | ✅ |
| LDAPI | ✅ |
| ASN.1 编解码 | ✅ |

### 限制说明

1. 纯 Perl 模块无传统二进制产物
2. 质量门禁 G4 检查需手动验证模块加载
3. 网络连接测试需要实际 LDAP 服务器

## 安装位置

```
/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0/Net/LDAP/
```

## 参考链接

- CPAN: https://metacpan.org/pod/Net::LDAP
- 源码: https://cpan.metacpan.org/authors/id/M/MA/MARSCHAP/perl-ldap-0.68.tar.gz

---

*OpenHarmony 编译归档 - 2026-06-13*