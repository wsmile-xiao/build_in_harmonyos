# perl-locale-maketext-fuzzy

Locale::Maketext::Fuzzy - 带模糊匹配功能的 Perl 本地化模块

## 软件信息

- **软件名**: perl-locale-maketext-fuzzy
- **模块名**: Locale::Maketext::Fuzzy
- **版本**: 0.11
- **来源**: CPAN
- **作者**: Audrey Tang
- **主页**: https://metacpan.org/pod/Locale::Maketext::Fuzzy

## 功能简介

Locale::Maketext::Fuzzy 是 Locale::Maketext 的扩展模块，提供模糊匹配功能。相比精确匹配，模糊匹配允许部分匹配 Lexicon 中的键，提高了本地化匹配的灵活性。

**核心特性**:
- 继承 Locale::Maketext 所有功能
- 支持模糊匹配翻译键
- 参数替换 [_1], [_2], ...
- `_AUTO` 模式自动返回原文

## 鸿蒙平台适配状态

| 版本 | 状态 | 测试结果 |
|------|------|---------|
| 0.11-r5 | ✅ 可用 | 全部通过 |

## 安装使用

### 1. 安装预编译包

从 cmd-pkgs 下载预编译包并安装：

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- perl-locale-maketext-fuzzy 0.11-r5
```

### 2. 设置环境变量

```bash
export PERL5LIB=/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0
```

### 3. 使用示例

```perl
use Locale::Maketext::Fuzzy;

package My::Localizer;
use base qw(Locale::Maketext::Fuzzy);

our %Lexicon = (
    _AUTO => 1,
    "Hello, [_1]!" => "你好，[_1]！",
    "Welcome" => "欢迎",
);

package main;

my $lh = My::Localizer->new;
print $lh->maketext("Hello, World!");  # 输出：你好，World！
print $lh->maketext("Welcome");         # 输出：欢迎
print $lh->maketext("Unknown");         # 输出：Unknown（_AUTO 模式）
```

## 依赖

- Perl 5.42.0
- Locale::Maketext（Perl 核心模块，已内置）

## 注意事项

1. **纯 Perl 模块** - 无 XS 代码，无 SELinux 加载限制，可直接使用
2. **安装路径** - 需正确设置 PERL5LIB 或使用 `-I` 参数
3. **模糊匹配** - 在 `_AUTO` 模式下，未精确匹配的短语返回原文

## 测试报告

详见 `0.11-r5/reports/test-report.md`

## 版本历史

- **0.11-r5** (2026-06-13): 首次适配，功能测试全部通过
- **0.11** (2026-06-13): 初始版本，有 manifest 缺失问题