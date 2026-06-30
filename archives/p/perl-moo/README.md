# perl-moo

**Moo** — Minimalist Object Orientation (with Moose compatibility)

## 软件描述

Moo 是 Perl 的轻量级面向对象编程框架，是 Moose 的精简替代方案。
它提供了类定义、属性声明、角色组合、方法修饰符等核心 OOP 功能，
同时保持与 Moose 的兼容性。Moo 是纯 Perl 实现，不包含 XS/C 代码，
因此在各种平台上具有极高的可移植性。

## 版本历史

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 2.005005 | published | 2026-06-23 | 纯 Perl 模块，鸿蒙平台完美兼容 |

## 使用说明

```perl
use Moo;

has 'name' => (is => 'ro', required => 1);
has 'age'  => (is => 'rw', default => sub { 0 });

sub greet {
    my $self = shift;
    return "Hello, I'm " . $self->name;
}
```

## 构建依赖

- perl >= 5.006
- Class::Method::Modifiers >= 1.10
- Role::Tiny >= 2.002003
- Sub::Defer >= 2.006006
- Sub::Quote >= 2.006006
- ExtUtils::MakeMaker (构建时)

## 许可证

Perl (Artistic License 1.0 / GPL)
