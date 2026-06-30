# Mail::Sendmail

Perl 邮件发送模块 - 鸿蒙平台预编译包

## 软件介绍

Mail::Sendmail 是一个简单、轻量的 Perl SMTP 邮件发送模块，无需复杂依赖即可发送邮件。

### 主要特性
- 简单易用的邮件发送接口
- 支持 SMTP 认证 (DIGEST-MD5, CRAM-MD5, PLAIN, LOGIN)
- 支持 MIME 邮件
- 轻量级，无 XS 依赖

### 技术信息
- **版本**: 0.82
- **许可证**: Perl Artistic License
- **构建系统**: ExtUtils::MakeMaker (Makefile.PL)
- **类型**: PurePerl 模块（无 XS）

## 鸿蒙平台适配

### 编译状态
- **编译日期**: 2026-06-15
- **平台**: OpenHarmony (aarch64-unknown-linux-ohos)
- **编译器**: clang 18.1.8
- **状态**: ✅ 编译成功

### 平台适配说明
- Sys::Hostname::Long 模块被设为可选（原为硬依赖）
- 使用 eval require + fallback 机制处理可选依赖
- 纯 Perl 模块，无 SELinux 加载限制

### 质量门禁
| 门禁 | 状态 | 说明 |
|------|------|------|
| G1 二进制完整性 | PASS | 无二进制文件（PurePerl） |
| G2 功能可用性 | PASS | 邮件发送功能正常 |
| G3 可移植性 | PASS | 无 ELF 文件 |
| G4 档案完整性 | PASS | 归档完整 |

## 使用方式

### 基本用法
```perl
use Mail::Sendmail;

%mail = (
    To      => 'recipient@example.com',
    From    => 'sender@example.com',
    Subject => 'Test Message',
    Message => "This is a test message.\n"
);

sendmail(%mail) or die $Mail::Sendmail::error;
```

### SMTP 认证
```perl
%mail = (
    To      => 'recipient@example.com',
    From    => 'sender@example.com',
    smtp    => 'smtp.example.com',
    auth    => {
        user => 'username',
        password => 'password',
        method => 'LOGIN'
    },
    Subject => 'Authenticated Message',
    Message => "Body text"
);
```

### 自定义 SMTP 服务器
```perl
# 在脚本中设置
$mailcfg{smtp} = ['smtp.example.com:25'];
```

## 安装

### 预编译包安装
```bash
# 解压预编译包
tar xzf perl-mail-sendmail-0.82-ohos-aarch64.tar.gz -C ~/usr/local

# 验证安装
perl -MMail::Sendmail -e 'print $Mail::Sendmail::VERSION'
# 输出: 0.82
```

## 平台适配要点

### Sys::Hostname::Long 可选化

原版代码将 `Sys::Hostname::Long` 作为硬依赖，但该模块在鸿蒙平台不一定可用。

**修改方案**：
```perl
# 原代码
use Sys::Hostname::Long;
$localhost = hostname_long() || hostname() || 'localhost';

# 修改后
eval { require Sys::Hostname::Long; Sys::Hostname::Long->import('hostname_long'); };
$localhost = (defined &hostname_long ? hostname_long() : '') || hostname() || 'localhost';
```

此修改：
- 保留 `Sys::Hostname::Long` 功能（若可用）
- 不阻塞邮件发送（若不可用）
- 使用 `Sys::Hostname` 作为 fallback

## 相关模块

- **Mail::Tools**: 邮件处理工具集
- **MIME::QuotedPrint**: MIME 编码（可选）
- **Sys::Hostname::Long**: 长主机名获取（可选）

## 版本信息

| 版本 | 状态 | 发布日期 |
|------|------|---------|
| 0.82 | published | 2026-06-15 |

## 相关链接
- CPAN：https://metacpan.org/pod/Mail::Sendmail