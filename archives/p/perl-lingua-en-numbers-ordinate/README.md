# Lingua::EN::Numbers::Ordinate

将基数数字（如 3）转换为序数形式（如 "3rd"）的 Perl 模块。

## 描述

Lingua::EN::Numbers::Ordinate 提供了将数字转换为英语序数词的功能：
- `ordinate(1)` → "1st"
- `ordinate(2)` → "2nd"
- `ordinate(3)` → "3rd"
- `ordinate(11)` → "11th"
- `ordinate(23)` → "23rd"

## 主要功能

- **ordinate(n)**: 返回数字的序数形式（默认导出）
- **ordsuf(n)**: 仅返回序数后缀（"st", "nd", "rd", "th"）
- **th(n)**: ordinate 的别名

## 依赖

- Perl 5.6+

## 版本历史

| 版本 | 状态 | 日期 |
|------|------|------|
| 1.05-r2 | published | 2026-06-15 |

## 鸿蒙平台说明

- 纯 Perl 模块，无需特殊编译参数
- 无 HMDFS 限制，可正常加载
- 用户需设置 PERL5LIB 环境变量

## 用法示例

```perl
use Lingua::EN::Numbers::Ordinate;

print ordinate(23);    # 输出: 23rd
print ordinate(11);    # 输出: 11th
print ordinate(101);   # 输出: 101st

use Lingua::EN::Numbers::Ordinate qw(ordsuf);
print ordsuf(3);       # 输出: rd
```

## 来源

- CPAN: https://metacpan.org/pod/Lingua::EN::Numbers::Ordinate
- 作者: Neil Bowers (NEILB)