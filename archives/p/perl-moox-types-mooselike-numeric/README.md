# perl-moox-types-mooselike-numeric

Moo types for numbers — 提供一组数值类型约束，用于 Moo-based 类的属性验证。

## 版本历史

| 版本 | 日期 | 状态 | 说明 |
|------|------|------|------|
| 1.03-r2 | 2026-06-24 | published | 鸿蒙平台编译，51 项官方测试全部通过 |

## 提供的类型约束

- `PositiveNum` — 正数
- `PositiveOrZeroNum` — 正数或零
- `PositiveInt` — 正整数
- `PositiveOrZeroInt` — 正整数或零
- `NegativeNum` — 负数
- `NegativeOrZeroNum` — 负数或零
- `NegativeInt` — 负整数
- `NegativeOrZeroInt` — 负整数或零
- `SingleDigit` — 单个数字 (0-9)

## 使用示例

```perl
package MyPackage;
use Moo;
use MooX::Types::MooseLike::Numeric qw(PositiveInt);

has count => (
  is  => 'rw',
  isa => PositiveInt,
);
```

## 运行时依赖

- MooX::Types::MooseLike >= 0.23
- Moo >= 1.004002

## 鸿蒙平台说明

纯 Perl 模块，无 C/XS 编译，可直接在 HMDFS 文件系统上加载使用，不受 SELinux 限制。
