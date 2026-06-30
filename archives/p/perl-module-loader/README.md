# perl-module-loader

Module::Loader — finding and loading modules in a given namespace

## 描述

Module::Loader 提供在指定命名空间下查找和加载 Perl 模块的功能，主要用于插件发现和加载场景。

核心功能：
- `find_modules($namespace)` — 搜索 @INC 中指定命名空间下的所有模块
- `search($namespace)` — 仅搜索直接子模块（max_depth=1）
- `load(@modules)` — 加载指定模块（基于 Module::Runtime）
- `max_depth` 属性 — 控制搜索深度

灵感来自 Mojo::Loader，但无需依赖 Mojolicious。

## 版本历史

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 0.04 | published | 2026-06-18 | OpenHarmony 平台适配，纯 Perl 模块无需补丁 |

## OpenHarmony 适配说明

### 平台兼容性

Module::Loader 是纯 Perl 模块，无 C/XS 扩展，在 OpenHarmony 平台上无需任何补丁即可编译和使用。

- **构建系统**: ExtUtils::MakeMaker (perl Makefile.PL)
- **编译产物**: 纯 .pm 文件，无二进制文件
- **SELinux**: 无限制（纯 Perl 模块不涉及 .so 加载）
- **G0 干净构建验证**: 手动验证通过（自动化脚本不支持 perl-makemaker 构建系统，为已知平台限制）

### 运行时依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| Path::Iterator::Rule | 1.015 | 目录遍历 |
| Number::Compare | 0.03 | Path::Iterator::Rule 依赖 |
| Text::Glob | 0.11 | Path::Iterator::Rule 依赖 |
| Path::Tiny | 0.150 | Path::Iterator::Rule 依赖 |
| Module::Runtime | 0.018 | 模块加载 |

## 使用方法

```perl
use Module::Loader;

my $loader  = Module::Loader->new;
my @plugins = $loader->find_modules('MyApp::Plugin');

foreach my $plugin (@plugins) {
    $loader->load($plugin);
}

# 限制搜索深度
my $loader = Module::Loader->new(max_depth => 1);
my @direct = $loader->search('MyApp::Plugin');
```

## 依赖

- Perl 5.6+
- Path::Iterator::Rule
- Module::Runtime
