# perl-namespace-autoclean

## 软件描述

namespace::autoclean — Perl 模块，用于在编译期自动清理导入到当前命名空间的符号，保持命名空间干净。常与 Moose、Moo、Mouse 等 Perl OO 框架配合使用，防止导入的工具函数污染类的公共 API。

## 版本

| 版本 | 状态 | 编译日期 |
|------|------|---------|
| 0.31 | published | 2026-06-24 |

## 构建系统

- 类型: makefile (ExtUtils::MakeMaker)
- 编译器: clang 18.1.8
- 构建: `perl Makefile.PL && make && make test && make install`

## 运行时依赖

- B::Hooks::EndOfScope >= 0.12
- namespace::clean >= 0.20
- List::Util
- Perl >= 5.006

## 平台特性

- **纯 Perl 模块**：无 XS 组件，不受 SELinux/HMDFS 限制
- 可直接在用户空间 (`~/usr/local`) 加载使用，无需管理员安装
- 与 perl-dbd-pg 等 XS 模块不同，无需 HNP 包安装到系统目录

## 鸿蒙兼容性

✅ 完全兼容 — 编译无修改，测试全通过 (217/217)，功能验证通过
