# perl-ppix-quotelike

PPIx::QuoteLike — 解析 Perl 字符串字面量和类字符串构造（q//、qq//、qw//、heredoc 等），以与 PPI 一致的方式生成 token 树。

## 功能概述

- 解析所有 Perl 引号类语法：`"..."`、`'...'`、`q//`、`qq//`、`qw//`、`qr//`、heredoc
- 生成 PPI 兼容的 Token 对象树，支持遍历和检查
- 检测字符串中的变量插值
- 提供 Dumper 工具用于调试输出
- 纯 Perl 实现，无 XS 依赖，跨平台兼容

## OHOS 适配

- **构建系统**：ExtUtils::MakeMaker (Makefile.PL)，纯 Perl 模块无 C 编译
- **关键环境变量**：
  - `PERL5LIB` 必须包含 `$DEFAULT_PREFIX/lib/site_perl/5.42.0`（PPI 模块安装路径）
  - `PERL_PARAMS_UTIL_PP=1` 使用纯 Perl 版本的 Params::Util（避免 XS .so dlopen 问题）
- **已知问题**：
  - Readonly 模块需要手动安装（Module::Build::Tiny 不可用时直接拷贝 .pm 文件）
  - SSL 证书验证失败时使用 `curl -k` 下载 tarball（参考 perl-dbd-pg 编译经验）
- **平台兼容性**：纯 Perl 模块，无平台相关二进制，aarch64-linux 完全兼容

## 依赖关系

### 编译依赖
- PPI (>= 1.238) — Perl 源码解析基础库
- Readonly — 只读变量支持
- Params::Util (纯 Perl 模式)

### 运行依赖
- Perl >= 5.006
- PPI::Document, PPI::Dumper (>= 1.238)
- Carp, Encode, Exporter, List::Util, Scalar::Util, Readonly

## 参考资料

- CPAN: https://metacpan.org/dist/PPIx-QuoteLike
- 源码仓库: https://github.com/trwyant/perl-PPIx-QuoteLike
- 许可证: Perl Artistic License (同 Perl 5.10.0)
