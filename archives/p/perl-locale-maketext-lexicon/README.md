# perl-locale-maketext-lexicon

Locale::Maketext::Lexicon - Use other catalog formats in Maketext

## 描述

Locale::Maketext::Lexicon 是一个 Perl 模块，为 Locale::Maketext 提供多种本地化文件格式的支持，包括：

- Gettext (.po/.mo)
- Msgcat (Unix catgets)
- Auto（自动生成）
- Tie（绑定变量）

还提供 `xgettext.pl` 工具用于从源码提取可翻译字符串。

## 已编译版本

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 1.00-r6 | built | 2026-06-15 | 当前版本，测试通过 |
| 1.00 | archived | 2026-06-13 | 旧版本 |

## 安装

```bash
# 设置 Perl 模块路径
export PERL5LIB=/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0

# 验证安装
perl -MLocale::Maketext::Lexicon -e 'print $Locale::Maketext::Lexicon::VERSION'
```

## 使用示例

```perl
use Locale::Maketext::Lexicon { en => ["Auto"] };
use Locale::Maketext::Lexicon { de => ["Gettext", "de.po"] };
```

## 依赖

- Perl 5.42.0
- Locale::Maketext 1.17

## 许可证

MIT

## 主页

https://metacpan.org/pod/Locale::Maketext::Lexicon