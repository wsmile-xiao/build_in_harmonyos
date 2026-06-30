# IO::Prompt::Tiny

## 简介

IO::Prompt::Tiny 是一个极其简单的 Perl 提示模块，提供带有默认选项的用户输入提示功能，基于 ExtUtils::MakeMaker 的 prompt 实现。

## 功能概述

- 提供简单的用户输入提示
- 支持默认选项
- 自动检测交互式环境
- 支持 PERL_MM_USE_DEFAULT 环境变量（非交互模式）

## OHOS 适配

### 适配要点

1. **纯 Perl 模块**：无需修改源码，无需编译原生代码
2. **安装路径问题**：安装路径不在 Perl 默认 @INC 中，需设置 PERL5LIB 环境变量
   ```bash
   PERL5LIB=/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0
   ```
3. **测试依赖缺失**：测试依赖 Capture::Tiny 未安装，测试失败但不影响运行时功能
4. **依赖均为核心模块**：Carp、Exporter 都是 Perl 核心模块

### 已知问题

- 测试套件失败（缺少 Capture::Tiny），但为非阻塞问题
- 需手动设置 PERL5LIB 才能正确加载模块

### 与 Linux 的差异

无差异，纯 Perl 模块跨平台行为一致。

## 排除与替代

无需要排除的功能。

## 依赖

### 编译依赖

- Perl 5.42.0
- ExtUtils::MakeMaker（核心模块）

### 运行依赖

- Carp（核心模块）
- Exporter（核心模块）

### 测试依赖（可选）

- Capture::Tiny ≥ 0.12（未安装，导致测试失败）

## 功能验证

### 加载验证

```bash
PERL5LIB=/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0 \
  perl -MIO::Prompt::Tiny -e 'print "Version: $IO::Prompt::Tiny::VERSION\n"'
# 输出: Version: 0.003
```

### 非交互模式验证

```bash
PERL5LIB=/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0 \
  perl -e 'use IO::Prompt::Tiny qw(prompt); $ENV{PERL_MM_USE_DEFAULT}=1; print prompt("Continue?", "y"), "\n"'
# 输出: y
```

## 参考

- CPAN: https://metacpan.org/pod/IO::Prompt::Tiny
- GitHub: https://github.com/dagolden/IO-Prompt-Tiny
- 作者: David Golden <dagolden@cpan.org>