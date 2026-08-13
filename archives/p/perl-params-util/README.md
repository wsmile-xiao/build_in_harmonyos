# perl-params-util

Simple, compact and correct param-checking functions (Perl XS module with pure Perl fallback).

## 软件信息

- **官网**: https://metacpan.org/dist/Params-Util
- **源码**: https://cpan.metacpan.org/authors/id/R/RE/REHSACK/Params-Util-1.102.tar.gz
- **许可证**: MIT
- **分类**: perl-library

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 1.102 | built | 2026-07-03 | 首次编译成功，conan-verify 全部门禁通过 |

## 运行依赖

- perl (5.42.0)

## 编译依赖

- musl (提供标准 C 库头文件: sys/types.h 等)

## 使用说明

Params::Util 提供简单、紧凑且正确的参数检查函数，包括 `_STRING`、`_NUMBER`、`_SCALAR` 等。

### 安装

预编译包通过 Conan 安装：
```bash
conan install --requires=perl-params-util/1.102
```

XS 模块安装到 `/data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/auto/Params/Util/` 目录。

### 注意事项

由于 SELinux HMDFS 限制，XS 模块 (.so) 需要安装到系统目录 `/data/service/hnp` 才能正常加载。

**纯 Perl 回退模式**：设置环境变量 `PERL_PARAMS_UTIL_PP=1` 可强制使用纯 Perl 实现（Params::Util::PP），无需 XS .so 加载，适用于无法安装到系统目录的场景。

---
*OpenHarmony 编译归档 · 2026-07-03*
