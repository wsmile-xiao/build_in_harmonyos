# perl-scope-guard

## 软件说明

Scope::Guard — Perl 的词法作用域资源管理模块（RAII 风格）。

提供三种调用方式：
- `guard { ... }` — 代码块语法
- `Scope::Guard->new(sub { ... })` — 构造器语法
- `scope_guard { ... }` — 函数语法

当 guard 对象离开作用域时（正常退出或异常），注册的清理代码自动执行。

## 版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 0.21 | published | 2026-06-29 |

## 构建系统

- **类型**: Perl (ExtUtils::MakeMaker)
- **依赖**: 无（纯 Perl 模块）
- **许可证**: perl_5

## 来源

- CPAN: [Scope-Guard-0.21](https://cpan.metacpan.org/authors/id/C/CH/CHOCOLATE/Scope-Guard-0.21.tar.gz)
- 作者: CHOCOLATE
