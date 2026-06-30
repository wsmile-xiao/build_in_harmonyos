# perl-ppi

PPI - Parse, Analyze and Manipulate Perl (Without Perl Itself)

## 版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 1.284 | ✅ published | 2026-06-26 |

## 描述

PPI (Parse Perl Isolated) 是一个纯 Perl 模块，用于解析、分析和操作 Perl 代码。它是 Perl 静态分析工具链的核心组件，提供完整的 Perl 语法树解析能力。

## 构建系统

- ExtUtils::MakeMaker (Makefile.PL)
- 纯 Perl 模块，无编译产物 (no .so/.a)

## 鸿蒙平台适配要点

1. **Clone XS 限制**: Clone 模块的 XS .so 在 HMDFS 上无法 dlopen (SELinux 限制)，使用 Storable::dclone 纯 Perl shim 替代
2. **Params::Util 纯 Perl 模式**: 设置 `PERL_PARAMS_UTIL_PP=1` 环境变量
3. **PERL5LIB 配置**: 需包含 `$DEFAULT_PREFIX/lib/site_perl/5.42.0`

## 依赖

| 依赖 | 类型 | 鸿蒙适配 |
|------|------|---------|
| Clone | XS → 纯Perl shim | Storable::dclone |
| Params::Util | XS → 纯Perl | PERL_PARAMS_UTIL_PP=1 |
| Safe::Isa | 纯Perl | 直接安装 |
| Task::Weaken | 纯Perl | 直接安装 |
| Class::Inspector | 纯Perl | 直接安装 |
| YAML::PP | 纯Perl | 直接安装 |

## Conan 配方

- Package: `perl-ppi/1.284@ohpcd/stable`
- Profile: `ohos-aarch64`
- G0-G4 + L2/L4/L5: 全部 PASS
