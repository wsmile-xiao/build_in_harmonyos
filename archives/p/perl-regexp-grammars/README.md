# perl-regexp-grammars

Regexp::Grammars - Extended regular expression grammar support for Perl.

## 描述

Regexp::Grammars 是一个纯 Perl 模块，为 Perl 正则表达式添加了类似解析器生成器的语法扩展能力。它允许在正则表达式中定义命名规则、子规则、动作代码块等，实现结构化的文本解析。

## 版本

| 版本 | 状态 | 编译日期 |
|------|------|---------|
| 1.058 | published | 2026-06-26 |

## 特点

- 纯 Perl 模块，无 XS/C 代码，无需编译器链接
- 构建系统：ExtUtils::MakeMaker (Makefile.PL)
- 支持命名规则、子规则调用、动作代码块
- 支持递归语法、自动分隔列表、对象规则
- 兼容 Perl 5.42.0

## 依赖

- Perl >= 5.10（推荐 5.42.0）

## 链接

- [CPAN](https://metacpan.org/dist/Regexp-Grammars)
- [作者](https://metacpan.org/author/DCONWAY)
