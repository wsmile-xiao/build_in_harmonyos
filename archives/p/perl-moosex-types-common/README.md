# perl-moosex-types-common

MooseX::Types::Common — Moose 类型约束的常用通用类型库。

## 版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 0.001015 | built | 2026-06-23 |

## 描述

提供 MooseX::Types 生态系统中常用的基础类型约束，包括：

- **MooseX::Types::Common::String**: 字符串类型 (SimpleStr, NonEmptyStr, Password, etc.)
- **MooseX::Types::Common::Numeric**: 数值类型 (PositiveNum, PositiveInt, SingleDigit, etc.)

纯 Perl 模块，无 XS/C 编译代码。

## 构建系统

Module::Build::Tiny (perl Build.PL + ./Build)

## 依赖

- perl >= 5.008
- Moose (运行时依赖)
- MooseX::Types (运行时依赖)
