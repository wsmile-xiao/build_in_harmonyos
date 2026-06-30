# Digest-HMAC

## 简介

Digest-HMAC 是 Perl 的 HMAC（Keyed-Hashing for Message Authentication）模块实现。HMAC 是一种使用密钥进行消息认证的机制，广泛应用于网络安全和数据完整性验证场景。

本模块提供了以下三个核心组件：
- **Digest::HMAC**: 通用 HMAC 框架
- **Digest::HMAC_MD5**: 基于 MD5 的 HMAC 实现
- **Digest::HMAC_SHA1**: 基于 SHA-1 的 HMAC 实现

## 特性

- 纯 Perl 实现，无 XS 组件，跨平台兼容性好
- 符合 RFC 2202 标准测试
- 简单易用的 API

## 依赖

- Perl 5.8+（推荐 5.42+）
- Digest::SHA（Perl 5.42+ 内置）
- Digest::MD5（Perl 5.42+ 内置）

## 鸿蒙平台适配说明

### ✅ 完全可用

- **测试状态**: 所有 RFC 2202 测试向量验证通过
- **依赖状态**: Perl 5.42+ 内置 Digest::SHA/MD5，无需额外安装
- **模块类型**: 纯 Perl 模块，无 XS 组件，无需 ELF 签名
- **功能验证**: HMAC-MD5 和 HMAC-SHA1 均正常工作，与 OpenSSL 结果一致

### 使用示例

```perl
use Digest::HMAC_SHA1;

my $hmac = Digest::HMAC_SHA1->new($secret_key);
$hmac->add($message);
my $signature = $hmac->hexdigest;
```

### 注意事项

- HMAC-SHA1 使用 Digest::SHA（Perl内置）而非 Digest::SHA1（CPAN）
- 无需设置 PERL5LIB，安装后自动可用

## 版本信息

| 版本 | 编译日期 | 状态 | 说明 |
|------|----------|------|------|
| 1.05 | 2026-06-10 | published | 最新稳定版本 |

## 安装

### 使用预编译包

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- Digest-HMAC 1.05
```

### 手动编译

```bash
wget http://cpan.metacpan.org/authors/id/A/AR/ARODLAND/Digest-HMAC-1.05.tar.gz
tar xzf Digest-HMAC-1.05.tar.gz
cd Digest-HMAC-1.05
perl Makefile.PL INSTALL_BASE=$HOME/usr/local
make
make test
make install
```

## 使用示例

```perl
use Digest::HMAC_SHA1;

my $hmac = Digest::HMAC_SHA1->new($key);
$hmac->add($data);
my $digest = $hmac->hexdigest;
```

## 归档信息

- **归档路径**: `archives/d/Digest-HMAC/`
- **维护者**: OpenHarmony 编译团队
- **源码**: CPAN (http://cpan.metacpan.org/)
- **License**: Perl Artistic License