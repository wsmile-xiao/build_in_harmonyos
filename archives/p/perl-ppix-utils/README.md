# perl-ppix-utils

**PPIx::Utils** — PPI 文档实用工具函数集

## 基本信息

| 项 | 值 |
|------|------|
| 软件名 | perl-ppix-utils |
| 版本 | 0.004 |
| 许可证 | Artistic-1.0-Perl OR GPL-1.0-or-later |
| 主页 | https://github.com/Grinnz/PPIx-Utils |
| 构建系统 | ExtUtils::MakeMaker (perl-eumm) |
| 平台 | OpenHarmony (aarch64) |
| 状态 | ✅ published |

## 描述

PPIx::Utils 提供了一组用于处理 PPI (Parse Perl Isolated) 文档的实用工具函数，包括：

- **PPIx::Utils::Classification** — 节点分类（is_perl_builtin, is_function_call, is_hash_key 等 29 个函数）
- **PPIx::Utils::Language** — 语言工具（precedence_of, symbol_without_sigil）
- **PPIx::Utils::Traversal** — 遍历工具（first_arg, parse_arg_list, splitNodes_on_comma 等 7 个函数）

## 依赖

| 依赖 | 最低版本 | 实际版本 |
|------|---------|---------|
| PPI | 1.250 | 1.284 |
| B::Keywords | 1.09 | 1.29 |
| Exporter | any | 5.79 |
| Scalar::Util | any | 1.68_01 |
| perl | 5.006 | 5.42.0 |

## 版本索引

| 版本 | 状态 | 日期 |
|------|------|------|
| 0.004 | published | 2026-06-26 |
