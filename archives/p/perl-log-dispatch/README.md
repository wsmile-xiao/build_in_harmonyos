# perl-log-dispatch

## 简介

Log::Dispatch 是一个 Perl 日志分发模块，用于将消息分发到一个或多个输出。

该模块管理一组 Log::Dispatch::* 输出对象，可以通过统一的接口进行日志记录。您可以创建一个 Log::Dispatch 对象，然后向其添加各种日志对象（如文件日志记录器或屏幕日志记录器）。然后调用 dispatch 对象的 log 方法，该方法将消息传递给每个对象，每个对象再决定是否接受消息以及如何处理它。

这使得只需调用单个方法就能将消息发送到日志文件、通过电子邮件、到屏幕以及任何其他地方，一旦创建了 dispatch 对象，您所需的代码就非常少。

## 功能特性

- 支持多种输出方式：文件、屏幕、邮件、Syslog 等
- 统一的日志接口
- 支持多种日志级别：debug、info、notice、warning、error、critical、alert、emergency
- 可扩展的输出类架构
- 支持回调函数处理消息

## 编译信息

- **版本**: 2.71
- **构建系统**: ExtUtils::MakeMaker (Makefile.PL)
- **许可证**: Artistic License 2.0
- **Perl 版本要求**: 5.006+

## 主要依赖

- Carp
- Devel::GlobalDestruction
- Dist::CheckConflicts (>= 0.02)
- Encode
- Module::Runtime
- Params::ValidationCompiler
- Scalar::Util
- Specio (>= 0.32)
- Sys::Syslog (>= 0.28)
- Try::Tiny
- namespace::autoclean

## 使用示例

```perl
use Log::Dispatch;

my $log = Log::Dispatch->new(
    outputs => [
        [ 'File',   min_level => 'debug', filename => 'logfile' ],
        [ 'Screen', min_level => 'warning' ],
    ],
);

$log->info('Blah, blah');
$log->warning('Something important');
```

## 来源

- 项目地址: https://github.com/houseabsolute/Log-Dispatch
- CPAN: https://metacpan.org/release/Log-Dispatch

## 上库状态

**当前状态**: ✅ published（已发布）

**上库条件检查**:
- ✅ 编译成功
- ✅ 预编译包已生成
- ✅ 质量门禁通过（G1-G4 PASS）
- ✅ 依赖模块已编译（Specio 0.48, namespace::autoclean 0.31, Params::ValidationCompiler 0.31, Module::Runtime 0.016, Eval::Closure 0.14, Exception::Class 1.45）
- ✅ 功能测试通过（模块可正常加载和输出日志）

**依赖链**（已完成）:
1. Module::Runtime 0.016 ✅
2. Eval::Closure 0.14 ✅
3. Exception::Class 1.45 ✅
4. Params::ValidationCompiler 0.31 ✅
5. Specio 0.48 ✅
6. namespace::autoclean 0.31 ✅
7. perl-log-dispatch 2.71 ✅

**版本**: 2.71
**发布日期**: 2026-06-16