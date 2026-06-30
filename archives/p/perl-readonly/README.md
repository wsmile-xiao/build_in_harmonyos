# perl-readonly

Perl 模块 `Readonly` — 创建只读标量、数组、哈希。

## 描述

`Readonly` 是一个纯 Perl 模块，提供创建只读变量的功能。支持标量 (Scalar)、数组 (Array)、哈希 (Hash) 以及嵌套数据结构。任何对只读变量的修改尝试都会导致程序 die。

主要功能：
- `Readonly::Scalar` — 创建只读标量
- `Readonly::Array` — 创建只读数组
- `Readonly::Hash` — 创建只读哈希
- `Readonly` — 通用接口，自动判断类型
- 深度只读保护，嵌套结构和引用同样不可修改
- 支持 `use Readonly qw(Readonly)` 导出

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 2.05 | published | 鸿蒙平台适配完成 |

## 构建系统

- ExtUtils::MakeMaker (Makefile.PL, 自动生成 fallback for Module::Build::Tiny)
- 纯 Perl 模块，无 C 编译

## 依赖

- Perl >= 5.005
- ExtUtils::MakeMaker (Perl 核心模块)
- 无外部依赖

## 链接

- [CPAN](https://metacpan.org/dist/Readonly)
- [GitHub](https://github.com/sanko/readonly)