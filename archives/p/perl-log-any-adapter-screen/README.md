# Log-Any-Adapter-Screen

Log::Any::Adapter::Screen - Send logs to screen, with colors and some other features

## 概述

这是一个 Log::Any 的屏幕适配器，提供日志输出到屏幕的功能，支持颜色输出和多种配置选项。

## 版本信息

- **版本**: 0.141
- **作者**: perlancar <perlancar@cpan.org>
- **许可证**: Perl 5 许可证

## 依赖

- Log::Any (>= 0)
- Log::Any::Adapter (>= 0.11)
- Term::ANSIColor
- Time::HiRes
- parent

## 安装

使用 ExtUtils::MakeMaker 标准 Perl 模块安装流程：

```bash
perl Makefile.PL
make
make test
make install
```

## 功能特点

- 带颜色的日志输出
- 支持日志级别过滤
- 支持自定义格式化
- 支持环境变量配置（LOG_LEVEL, TRACE, DEBUG, VERBOSE, QUIET）

## 使用示例

```perl
use Log::Any qw($log);
use Log::Any::Adapter;

Log::Any::Adapter->set('Screen');
$log->info("Information message");
$log->warn("Warning message");
$log->error("Error message");
```

## 鸿蒙平台状态

- ✅ 编译通过
- ✅ 测试通过
- ✅ 功能正常

---

*此 README 来自源码包，由 OpenDesk AI Agent 整理*