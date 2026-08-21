# perl-string-rewriteprefix

> String::RewritePrefix — rewrite strings based on a set of known prefixes

## 简介

String::RewritePrefix 是一个纯 Perl 模块，用于根据已知前缀集合重写字符串。
它可以将带有前缀标记的字符串列表按照规则进行前缀替换，支持字符串前缀和代码引用（coderef）前缀。

典型用例：将 `qw(Plugin Mixin Addon +Corporate::Thinger)` 重写为 `qw(MyApp::Plugin MyApp::Mixin MyApp::Addon Corporate::Thinger)`。

## 版本

| 版本 | 状态 | 编译日期 |
|------|------|---------|
| 0.009-r1 | built | 2026-07-06 |

## 构建系统

- **类型**: Perl ExtUtils::MakeMaker (Makefile.PL)
- **语言**: 纯 Perl（无 C/XS 代码）

## 依赖

### 运行时
- Perl >= 5.012
- Sub::Exporter >= 0.972
- Params::Util（通过 Sub::Exporter 间接依赖）

### OHOS 平台注意事项
- 需设置 `PERL_PARAMS_UTIL_PP=1` 环境变量（绕过 Params::Util XS .so 的 SELinux/HMDFS 加载限制）
- 需设置 `PERL5LIB` 包含 Sub::Exporter 依赖链路径

## 许可证

Perl_5（与 Perl 本身相同的许可证）
