# Mail::SPF

Perl SPF 记录验证模块 - 鸿蒙平台预编译包

## 软件介绍

Mail::SPF 是一个 Perl 模块，用于实现 Sender Policy Framework (SPF) 协议，验证邮件发送者的身份。

### 主要特性
- SPF 记录查询和解析
- 发送者身份验证
- 支持 SPF v1 和 v2 (Sender ID) 记录
- 命令行查询工具 (spfquery)
- SPF 查询守护进程 (spfd)

### 技术信息
- **版本**: 3.20250505
- **许可证**: BSD License
- **构建系统**: ExtUtils::MakeMaker (Makefile.PL)
- **类型**: PurePerl 模块（无 XS）

## 鸿蒙平台适配

### 编译状态
- **编译日期**: 2026-06-15
- **平台**: OpenHarmony (aarch64-unknown-linux-ohos)
- **Perl 版本**: 5.42.0
- **编译器**: clang 18.1.8
- **状态**: ✅ 编译成功

### 平台适配说明
- 纯 Perl 实现，无 XS 模块依赖
- 无特殊平台限制
- 所有功能均可正常使用

### 质量门禁
| 门禁 | 状态 | 说明 |
|------|------|------|
| G1 二进制完整性 | PASS | 无二进制文件 |
| G2 功能可用性 | PASS | SPF 查询功能可用 |
| G3 可移植性 | PASS | 无平台限制 |
| G4 档案完整性 | PASS | 归档完整 |

## 使用方式

### SPF 记录查询
```perl
use Mail::SPF;

# 创建 SPF 查询对象
my $spf = Mail::SPF->new(
    ip_address => '192.0.2.1',
    sender     => 'user@example.com',
);

# 执行查询
my $result = $spf->result();
print "Result: $result\n";  # pass, fail, neutral, etc.
```

### 命令行查询
```bash
# 使用 spfquery 工具
spfquery --ip-address=192.0.2.1 --sender=user@example.com

# 使用 spfd 守护进程
spfd --port=5920
```

## 安装

### 预编译包安装
```bash
# 解压预编译包
tar xzf perl-mail-spf-3.20250505-ohos-aarch64.tar.gz -C ~/usr/local

# 验证安装
perl -MMail::SPF -e 'print $Mail::SPF::VERSION'
```

## 依赖

### 必需依赖
- perl >= 5.10
- perl-net-dns（DNS 查询）
- perl-uri（URI 解析）

### 可选依赖
- Net::DNS::Resolver（自定义 DNS 解析器）

## 相关模块

- perl-mail-dkim（DKIM 签名验证）
- perl-mail-imapclient（IMAP 客户端）
- perl-mailtools（邮件处理工具）

## 版本信息

| 版本 | 状态 | 发布日期 |
|------|------|---------|
| 3.20250505 | published | 2026-06-15 |

## 相关链接
- CPAN: https://metacpan.org/pod/Mail::SPF
- SPF 协议: https://www.rfc-editor.org/rfc/rfc7208