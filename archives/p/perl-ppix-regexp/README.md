# perl-ppix-regexp

PPIx::Regexp — 解析 Perl 正则表达式，以与 PPI 一致的方式生成 token 树。支持 `qr//`、`m//`、`s///` 等正则构造形式。

## 功能概述

- 解析所有 Perl 正则语法：`qr//`、`m//`、`s///`、`(?{...})` 等
- 生成 PPI 兼容的 Token 对象树，支持遍历、检查和修改
- 支持 Unicode 属性、字符类、回溯引用、命名捕获等高级特性
- 提供 Lexer（词法分析）和 Dumper（调试输出）工具
- 纯 Perl 实现，无 XS 依赖，跨平台兼容

## OHOS 适配

- **构建系统**：ExtUtils::MakeMaker (Makefile.PL)，纯 Perl 模块无 C 编译
- **关键环境变量**：
  - `PERL5LIB` 必须包含 `$DEFAULT_PREFIX/lib/site_perl/5.42.0`（PPI 模块安装路径）
  - `PERL_PARAMS_UTIL_PP=1` 使用纯 Perl 版本的 Params::Util（避免 XS .so dlopen 问题）
- **已知问题**：
  - `PPIx::Regexp::Tokenizer->new()` 不接受 `qr//` 编译后的 Regexp 引用对象，必须使用字符串形式如 `"qr/foo/"`
  - SSL 证书验证失败时使用 `curl -k` 下载 tarball（参考 perl-dbd-pg 编译经验）
- **平台兼容性**：纯 Perl 模块，无平台相关二进制，aarch64-linux 完全兼容

## 依赖关系

### 编译依赖
- PPI (>= 1.238) — Perl 源码解析基础库
- Params::Util (纯 Perl 模式)

### 运行依赖
- Perl >= 5.006
- PPI::Document (>= 1.238)
- Carp, Exporter, List::Util, Scalar::Util

## 参考资料

- CPAN: https://metacpan.org/dist/PPIx-Regexp
- 源码仓库: https://github.com/trwyant/perl-PPIx-Regexp
- 许可证: MIT
