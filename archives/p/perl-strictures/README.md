# perl-strictures

Turn on strict and make most warnings fatal (Perl module).

## 软件信息

- **官网**: https://metacpan.org/dist/strictures
- **源码**: https://cpan.metacpan.org/authors/id/H/HA/HAARG/strictures-2.000006.tar.gz
- **许可证**: GPL-1.0-or-later OR Artistic-1.0-Perl
- **分类**: perl
- **作者**: HAARG

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 2.000006-r4 | built | 2026-07-06 | 纯 Perl 模块，CI 模拟通过 |

## 运行依赖

- perl (>= 5.006)

## 编译依赖

无（纯 Perl 模块，不需要 C 编译器）

## 使用说明

strictures 是一个 Perl 模块，用于一次性启用 strict 和 fatal warnings，减少每个文件头部 `use strict; use warnings;` 的重复代码。

### 安装

通过 Conan 安装：
```bash
conan install --requires=perl-strictures/2.000006-r4@ohpcd/stable
```

安装后 .pm 文件位于包的 `lib/` 目录下：
- `lib/strictures.pm` — 主模块
- `lib/strictures/extra.pm` — 额外检查模块

### 注意事项

- 纯 Perl 模块，无 C/XS 编译，不受鸿蒙 CRT 文件缺失影响
- SELinux HMDFS 限制导致 XS 编译器检查失败，模块自动回退纯 Perl 模式，不影响功能
- `/tmp` 只读，编译时使用 `$TMPDIR` 代替

---
*OpenHarmony 编译归档 · 2026-07-06*
