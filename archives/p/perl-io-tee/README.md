# perl-io-tee

IO::Tee - Perl 模块，用于将输出同时写入多个文件句柄

## 描述

IO::Tee 是一个 Perl 模块，提供类似 Unix `tee` 命令的功能，允许将数据同时写入多个目标。它继承自 IO::Handle，支持所有标准的文件句柄操作方法。

## 版本信息

| 版本 | 状态 | 日期 |
|------|------|------|
| 0.66 | built | 2026-06-11 |

**注意**: CPAN 发布的 IO-Tee-0.66.tar.gz 实际代码版本为 0.65。

## 功能特性

- 将输出同时写入多个文件
- 支持任意数量的输出目标
- 继承 IO::Handle 的所有方法
- 纯 Perl 实现，无需编译

## 依赖

- Perl 5.42.0（系统预装）
- 核心模块: Carp, IO::File, IO::Handle, Symbol, parent, strict, warnings

## 安装

### 预编译包安装

```bash
# 通过 cmd-pkgs 安装
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- perl-io-tee 0.66
```

### 手动安装

```bash
# 解压预编译包到用户目录
tar xzf perl-io-tee-0.66-ohos-aarch64.tar.gz -C /
```

## 使用方法

```perl
use lib '/storage/Users/currentUser/usr/local/lib/perl5';
use IO::Tee;
use IO::File;

# 同时写入多个文件
my $fh1 = IO::File->new('output1.txt', 'w');
my $fh2 = IO::File->new('output2.txt', 'w');
my $tee = IO::Tee->new($fh1, $fh2);

$tee->print("This line goes to both files\n");
$tee->close();
```

## 测试结果

| 测试项 | 结果 |
|--------|------|
| 模块加载 | ✅ PASS |
| 多文件写入 | ✅ PASS |
| 方法继承 | ✅ PASS |

## 许可证

Perl Artistic License

## 来源

- CPAN: https://cpan.metacpan.org/authors/id/N/NE/NEILB/IO-Tee-0.66.tar.gz
- 作者: NEILB