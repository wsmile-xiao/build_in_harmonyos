# Lingua::Preferred - Perl 语言偏好选择模块

## 软件简介

Lingua::Preferred 是一个 Perl 模块，用于在多语言环境下选择最佳语言。它模拟了 HTTP Accept-Language 协商机制，帮助应用程序根据用户的语言偏好选择合适的语言版本。

## 核心功能

### which_lang()

从用户理解的语言列表和可用语言列表中选择最佳语言：

```perl
use Lingua::Preferred qw(which_lang);

my @wanted = qw(en de fr it de_CH);      # 用户理解的语言
my @available = qw(fr it de);            # 服务器可用的语言

my $which = which_lang(\@wanted, \@available);
print "最佳语言: $which\n";              # 输出: de
```

### acceptable_lang()

判断某个语言是否在用户可接受范围内：

```perl
use Lingua::Preferred qw(acceptable_lang);

my @wanted = qw(en de fr);
if (acceptable_lang(\@wanted, 'de_DE')) {
    print "de_DE 是可接受的\n";          # 输出: 可接受（方言匹配）
}
```

## 特色功能

1. **方言匹配**：支持语言方言的智能匹配（如 `en_GB` 可匹配 `en_US`）
2. **通配符支持**：支持 `de_*` 等通配符匹配所有德语方言
3. **特殊值 'C'**：表示选择第一个可用语言（类似 Unix locale）
4. **优先级排序**：按用户偏好顺序选择最佳语言

## 适用场景

- Web 应用多语言页面选择
- 文档本地化系统
- 国际化应用的语言协商
- CLI 工具的多语言输出

## 技术特性

- **类型**：纯 Perl 模块（无 XS 代码）
- **依赖**：无强制依赖，可选依赖 Log::TraceMessages
- **测试覆盖**：76 个测试用例
- **许可证**：GPL-2.0 或 Artistic License（与 Perl 相同）

## 版本信息

- **当前版本**：0.2.4-r5
- **上游版本**：0.2.4
- **发布日期**：2003-12-14（上游）
- **鸿蒙适配**：2026-06-12

## 作者

Ed Avis <ed@membled.com>

## 注意事项

根据作者说明，此模块是作者自己代码的打包版本，不建议在需要进一步开发的项目中使用。对于新的项目，建议使用标准的 HTTP 语言协商或 gettext 方案。