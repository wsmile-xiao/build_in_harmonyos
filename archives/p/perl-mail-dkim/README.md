# Mail::DKIM

Perl DKIM 签名验证模块 - 鸿蒙平台预编译包

## 软件介绍

Mail::DKIM 是 Perl 的 DKIM (DomainKeys Identified Mail) 签名验证和生成模块，用于邮件系统的安全签名验证。

### 主要特性
- DKIM 签名验证
- DKIM 签名生成
- ARC (Authenticated Received Chain) 支持
- ed25519 签名支持
- 纯 Perl 实现

### 技术信息
- **版本**: 1.20240923
- **许可证**: Perl Artistic License
- **构建系统**: ExtUtils::MakeMaker (Makefile.PL)
- **类型**: 纯 Perl 模块

## 鸿蒙平台适配

### 编译状态
- **编译日期**: 2026-06-15
- **平台**: OpenHarmony (aarch64-unknown-linux-ohos)
- **Perl版本**: 5.42.0
- **状态**: ✅ 编译成功

### 质量门禁
| 门禁 | 状态 | 说明 |
|------|------|------|
| G1 二进制完整性 | PASS | 无二进制文件 |
| G2 功能可用性 | PASS | 基础模块可加载 |
| G3 可移植性 | PASS | 纯 Perl 无移植问题 |
| G4 档案完整性 | PASS | 归档完整 |

### 运行时依赖
Mail::DKIM 是纯 Perl 模块，但需要以下运行时依赖：
- **Crypt::OpenSSL::RSA**: 签名验证必需
- **Crypt::PK::Ed25519**: ed25519 签名支持（可选）

**当前状态**: 模块编译成功可安装，签名功能需要安装 Crypt::OpenSSL::RSA 依赖后才能使用。

## 使用方式

### 基础模块加载
```perl
use Mail::DKIM;
print "Mail::DKIM version: $Mail::DKIM::VERSION\n";
```

### 签名验证（需要依赖）
```perl
use Mail::DKIM::Verifier;
# 需要 Crypt::OpenSSL::RSA 已安装
my $dkim = Mail::DKIM::Verifier->new();
```

### 签名生成（需要依赖）
```perl
use Mail::DKIM::Signer;
# 需要 Crypt::OpenSSL::RSA 已安装
my $signer = Mail::DKIM::Signer->new(
    Algorithm => "rsa-sha256",
    Domain => "example.com",
    Selector => "default",
);
```

## 安装

### 预编译包安装
```bash
# 解压预编译包
tar xzf perl-mail-dkim-1.20240923-ohos-aarch64.tar.gz -C ~/usr/local

# 验证安装
perl -MMail::DKIM -e 'print $Mail::DKIM::VERSION'
# 输出: 1.20240923
```

## 相关模块

- **Mail::AuthenticationResults**: 验证结果处理
- **Mail::SPF**: SPF 验证
- **Net::DNS**: DNS 查询

## 版本信息

| 版本 | 状态 | 发布日期 |
|------|------|---------|
| 1.20240923 | published | 2026-06-15 |

## 相关链接
- CPAN：https://metacpan.org/pod/Mail::DKIM
- GitHub：https://github.com/msimerson/mail-dkim