# perl-moosex-types (MooseX::Types)

## 描述

MooseX::Types 为 Moose 提供灵活的类型约束组织方式。允许将类型约束组织成库，提供导出、子类型、联合、强制转换等功能。

## 版本历史

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 0.51 | published | 2026-06-24 | 纯Perl模块，测试全通过（20/20, 250 tests） |

## 构建说明

- **构建系统**: Module::Build::Tiny (Build.PL)
- **Perl 版本**: 5.42.0
- **配置命令**: `perl Build.PL --install_base $DEFAULT_PREFIX`
- **编译命令**: `./Build`
- **安装命令**: `./Build install`

## 运行时依赖

- Moose >= 1.06（实际安装 2.4000）
- Carp::Clan >= 6.00（实际安装 6.08）
- Sub::Exporter::ForMethods >= 0.100052

## 使用示例

```perl
use MooseX::Types -declare => [qw(PositiveInt)];
use MooseX::Types::Moose qw(Int);

subtype PositiveInt,
    as Int,
    where { $_ > 0 };
```
