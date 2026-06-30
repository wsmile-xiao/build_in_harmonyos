# Log::Any - Perl 日志库

## 简介

Log::Any 是一个 Perl 日志抽象库，提供统一的日志接口，可以将日志输出到任意后端（文件、屏幕、syslog 等）。

## 功能概述

- **统一的日志接口**：提供标准化的日志方法（debug、info、warn、error 等）
- **适配器模式**：支持多种输出后端，可灵活切换
- **零依赖**：纯 Perl 实现，无需额外 C 库
- **生产级质量**：广泛应用于 CPAN 生态系统

## OHOS 适配

### 适配要点

1. **纯 Perl 模块**：无需 C 编译器，构建简单
2. **构建系统**：使用 Makefile.PL（ExtUtils::MakeMaker）
3. **测试覆盖**：310 个测试用例全部通过

### 已知问题

无。模块在鸿蒙平台上运行正常。

### 与 Linux 的差异

无明显差异。纯 Perl 模块在两个平台表现一致。

## 依赖关系

### 编译依赖

- Perl 5.42.0+
- ExtUtils::MakeMaker 7.76+

### 运行依赖

- Perl 5.42.0+

## 编译方法

```bash
# 从 CPAN 下载源码
wget https://cpan.metacpan.org/authors/id/P/PR/PRBRENAN/Log-Any-1.718.tar.gz

# 解压并构建
tar xzf Log-Any-1.718.tar.gz
cd Log-Any-1.718
perl Makefile.PL PREFIX=$HOME/usr/local
make
make test
make install
```

## 参考资料

- CPAN: https://metacpan.org/pod/Log::Any
- GitHub: https://github.com/PRBrenan/Log-Any