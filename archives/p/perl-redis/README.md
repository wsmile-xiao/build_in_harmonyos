# perl-redis

Perl binding for Redis database — 纯 Perl 模块（无 XS/C 代码）。

## 描述

Redis 模块提供 Perl 语言对 Redis 数据库的访问接口，支持：
- Redis 全部命令（通过 AUTOLOAD 动态分发）
- 发布/订阅（Pub/Sub）模式
- 管道（Pipeline）操作
- 非阻塞 I/O
- 自动重连
- Redis Sentinel 支持
- Redis::Hash / Redis::List tie 接口

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|---------|
| 2.000 | published | 2026-06-29 |

## 构建系统

ExtUtils::MakeMaker (Makefile.PL) — 源码同时包含 Build.PL (Module::Build::Tiny) 和 Makefile.PL (ExtUtils::MakeMaker fallback)。使用 Makefile.PL 时需设置 `PERL_MM_FALLBACK_SILENCE_WARNING=1`。

## 依赖

### 运行时依赖
- `IO::Socket::Timeout` 0.32（依赖 `PerlIO::via::Timeout` 0.32）
- `Try::Tiny` 0.31

### 可选依赖
- `redis-server`（测试需要，鸿蒙平台不可用，相关测试跳过）

## 许可证

Artistic-2.0
