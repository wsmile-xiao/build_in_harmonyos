# perl-ref-util

Utility functions for checking references — Pure Perl module (Ref::Util, no XS/C code).

## 版本

- **0.204** (2026-06-26 编译, 2026-06-29 修复完善)

## 源码

- **上游**: https://cpan.metacpan.org/authors/id/A/AR/ARC/Ref-Util-0.204.tar.gz
- **SHA256**: `415fa73dbacf44f3d5d79c14888cc994562720ab468e6f71f91cd1f769f105e1`
- **许可证**: MIT

## 构建系统

ExtUtils::MakeMaker (Makefile.PL) — 使用 `PUREPERL_ONLY=1` 跳过可选的 Ref::Util::XS 依赖，以纯 Perl 模式构建。

## 依赖

### 运行时依赖
- 无额外依赖 (Exporter >= 5.57 是 Perl 5.42 核心模块)

### 可选依赖（未安装，测试时跳过）
- `Readonly` — 用于 `t/magic-readonly.t` 测试
- `Ref::Util::XS` — XS 加速版本（使用 PUREPERL_ONLY=1 跳过）

## 产物

| 文件 | 说明 |
|------|------|
| `lib/perl5/site_perl/5.42.0/Ref/Util.pm` | 主模块 |
| `lib/perl5/site_perl/5.42.0/Ref/Util/PP.pm` | 纯 Perl 实现后端 |

## API

提供以下引用检查函数：
- `is_ref($x)` — 检查是否为引用
- `is_arrayref($x)` — 检查是否为数组引用
- `is_hashref($x)` — 检查是否为哈希引用
- `is_scalarref($x)` — 检查是否为标量引用
- `is_coderef($x)` — 检查是否为代码引用
- `is_ref_type($x, $type)` — 检查引用类型

## 鸿蒙平台适配说明

- 纯 Perl 模块，无 XS/C 代码，无需交叉编译
- 468 项测试，465 通过，3 跳过（均为可选依赖，预期行为）
- 编译验证和 Conan 配方验证全部通过
- G0 门禁 E007 (autotools config.guess) 警告为误报 — 本模块不使用 autotools
