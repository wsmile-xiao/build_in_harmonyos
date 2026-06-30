# perl-provide

Perl 模块 `provide` — 根据 Perl 版本号选择不同的实现模块。

## 描述

`provide` 是一个纯 Perl 模块，允许开发者根据检测到的 Perl 版本轻松切换不同的实现模块。使用 `use provide` 语法时，会自动：

1. 让调用包继承 Exporter
2. 根据版本条件加载合适的实现模块
3. 将实现模块导出的函数重导出到调用包

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.03 | published | 鸿蒙平台适配完成 |

## 构建系统

- ExtUtils::MakeMaker (Makefile.PL)
- 纯 Perl 模块，无 C 编译

## 依赖

- Perl >= 5.8.8
- Exporter (Perl 核心模块)

## 链接

- [CPAN](https://metacpan.org/dist/provide)
- [GitHub](https://github.com/belden/perl-provide)
