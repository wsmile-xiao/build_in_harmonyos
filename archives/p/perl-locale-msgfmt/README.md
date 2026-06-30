# perl-locale-msgfmt

Locale::Msgfmt — 纯 Perl 实现的 .po → .mo 编译工具

## 简介

Locale::Msgfmt 是 GNU gettext msgfmt 的纯 Perl 实现，用于将 .po 翻译文件编译为 .mo 二进制消息目录文件。相比 C 版本的 msgfmt，它更易安装（通过 CPAN），更可移植，并支持目录批量编译。

## 版本

- 当前版本: 0.15-r2
- 状态: built

## 功能特性

- ✅ 单文件 .po → .mo 编译
- ✅ 目录批量编译（自动处理整个 .po 目录）
- ✅ 自动推测输出文件名（未指定 -o 时）
- ✅ 支持多语言（中文、日文等）
- ✅ 支持上下文翻译和 ngettext

## 在 OpenHarmony 上的使用

### 环境变量

```bash
export PERL5LIB=$HOME/usr/local/lib/site_perl/5.42.0:$HOME/usr/local/lib/perl5:$PERL5LIB
```

### Perl API

```perl
use Locale::Msgfmt;

# 单文件编译
Locale::Msgfmt::msgfmt({in => "messages.po", out => "messages.mo"});

# 目录批量编译
Locale::Msgfmt::msgfmt({in => "po_dir/", out => "mo_dir/"});
```

### 命令行

```bash
perl script/msgfmt.pl -o output.mo input.po
```

或使用系统安装的 GNU msgfmt：

```bash
msgfmt input.po -o output.mo
```

## 构建信息

- 构建系统: perl (Module::Install DSL)
- 构建参数: `perl -I. Makefile.PL INSTALL_BASE=$DEFAULT_PREFIX`
- 无补丁（纯 Perl 模块，不需要修改源码）
- 测试: 4 files, 16 tests, All successful

## 与 GNU msgfmt 的对比

| 特性 | Locale::Msgfmt | GNU msgfmt |
|------|---------------|------------|
| 实现 | 纯 Perl | C |
| 安装 | CPAN | 系统包 |
| .mo 格式 | 简化（无 hash） | 完整 |
| Java/C# 模式 | ❌ | ✅ |
| 可移植性 | ✅ 高 | ❌ 依赖平台 |
| 输出大小 | 较小 | 较大 |

两者生成的 .mo 文件格式兼容，运行时可互换使用。

## 依赖

- Perl 5.42.0
- File::Spec 0.80+ (系统自带)
- File::Path (系统自带，用于目录批量编译)

## 注意事项

1. 纯 Perl 模块，无需 ELF 签名
2. Module::Install::Msgfmt 是构建时依赖，运行时不需要
3. 目录批量编译时需确保 File::Path 模块可用
