# perl-string-random

Perl 模块，基于模式生成随机字符串。

## 软件信息

- **官网**: https://metacpan.org/release/String-Random
- **源码**: https://github.com/shlomif/string-random
- **许可证**: Artistic-1.0-Perl OR GPL-1.0-or-later
- **分类**: text

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 0.32-r2 | published | 2026-07-03 | 纯 Perl 模块，conan-verify 全部通过 |

## 运行依赖

- perl (>=5.10)

## 编译依赖

- perl (ExtUtils::MakeMaker)

## 使用说明

String::Random 提供基于模式生成随机字符串的功能，支持两种模式：

1. **randpattern** — 使用单字符模式（C=大写字母, c=小写字母, n=数字, !=特殊字符, .=任意, s=空格等）
2. **randregex** — 使用正则表达式模式生成随机字符串

### 安装

通过 Conan 安装：
```bash
conan install --requires=perl-string-random/0.32-r2
```

模块安装路径：`data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/String/Random.pm`

### 示例

```perl
use String::Random;

my $sr = String::Random->new();
my $password = $sr->randpattern("Ccn!Ccn!");  # 生成随机密码
my $code = $sr->randregex("\\d{4}");           # 生成4位随机数字
```

### 注意事项

- 纯 Perl 模块，无需 C 编译器，不受 CRT 文件缺失影响（与 perl-dbd-pg 等 XS 模块不同）
- 上游使用 Module::Build (Build.PL)，OHOS Perl 仅有 ExtUtils::MakeMaker，通过在 conanfile.py build() 中生成 Makefile.PL 适配
- 运行时依赖（Carp, Exporter, parent）均为 Perl 核心模块，无需额外安装

---
*OpenHarmony 编译归档 · 2026-07-06*
