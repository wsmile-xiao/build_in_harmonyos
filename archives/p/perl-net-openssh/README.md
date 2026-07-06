# perl-net-openssh

Perl SSH client package implemented on top of OpenSSH.

## 描述

Net::OpenSSH 是一个基于 OpenSSH `ssh` 命令的 Perl SSH 客户端模块。它通过创建 SSH master 连接（控制复用）来高效执行远程命令，支持 SFTP、SCP、rsync 等多种文件传输方式。

## 版本历史

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 0.84-r1 | published | 2026-06-26 | 鸿蒙平台适配版本，纯Perl模块 |

## 使用说明

### 安装

通过 Conan 安装：

```bash
conan install --requires=perl-net-openssh/0.84-r1
```

安装后设置 PERL5LIB 环境变量指向包的 `lib/perl5` 目录。

### 使用示例

```perl
use Net::OpenSSH;

# 注意：HMDFS文件系统上需设置 strict_mode => 0
my $ssh = Net::OpenSSH->new('user@host',
    strict_mode => 0,  # 鸿蒙平台必需
    master_opts => [-o => 'StrictHostKeyChecking=no'],
);

# 执行远程命令
my $output = $ssh->capture('ls -la');

# SFTP 文件传输
$ssh->scp_get('/remote/file', '/local/path');
$ssh->scp_put('/local/file', '/remote/path');

# SFTP 操作
my $sftp = $ssh->sftp;
$sftp->put('/local/file', '/remote/file');
```

## 鸿蒙平台适配说明

1. **纯Perl模块**：无XS/C代码，不受SELinux HMDFS限制影响，可通过PERL5LIB直接加载
2. **ctl_dir安全检查**：HMDFS文件系统chmod不生效（E046），目录权限为2771（setgid+group writable），Net::OpenSSH的`_is_secure_path`检查会拒绝。需设置`strict_mode => 0`绕过
3. **SSH客户端依赖**：需要系统安装openssh客户端（`/usr/bin/ssh`，OpenSSH 9.6p1）
4. **构建系统**：使用ExtUtils::MakeMaker（`perl Makefile.PL`），非标准autotools/CMake

## 构建系统

- **构建工具**: ExtUtils::MakeMaker (perl Makefile.PL)
- **Perl版本**: 5.42.0 (aarch64-linux)
- **编译器**: 无需C/C++编译器（纯Perl模块）

## 许可证

Perl 5 (perl_5)
