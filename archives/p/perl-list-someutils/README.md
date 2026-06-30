# perl-list-someutils

List::SomeUtils 是一个 Perl 模块，提供各种列表/数组处理实用函数。

## 功能概述

该模块提供以下主要函数：

- **uniq** / **distinct** - 去除重复元素
- **any** / **all** / **none** / **notall** - 逻辑判断函数
- **firstval** / **lastval** - 查找第一个/最后一个匹配值
- **first_index** / **last_index** - 查找索引
- **pairwise** - 两数组配对操作
- **minmax** - 同时获取最小和最大值
- **mesh** / **zip** - 合并多个数组
- **insert_after** - 在匹配元素后插入
- **bsearch** / **bsearch_index** - 二分查找
- **sort_by** / **nsort_by** - 按指定条件排序
- **singleton** - 获取只出现一次的元素

## 鸿蒙平台适配说明

### 编译模式

本模块在鸿蒙平台使用 **纯 Perl 模式**（PUREPERL_ONLY=1）编译：

- 不编译 XS 扩展，仅使用纯 Perl 实现
- 避免 XS 编译的平台兼容性问题
- 性能略有下降，但功能完全可用

### 使用方法

```perl
use List::SomeUtils qw(uniq any all pairwise);

# 去除重复元素
my @unique = uniq(1, 1, 2, 2, 3);  # [1, 2, 3]

# 检查是否存在匹配元素
my $has_even = any { $_ % 2 == 0 } (1, 2, 3, 4, 5);  # true

# 检查全部元素是否匹配
my $all_positive = all { $_ > 0 } (1, 2, 3);  # true

# 两数组配对操作
my @sums = pairwise { $a + $b } (1, 2, 3), (10, 20, 30);  # [11, 22, 33]
```

### 已测试功能

以下函数已在鸿蒙平台验证通过：

| 函数 | 测试状态 |
|------|----------|
| uniq | ✅ PASS |
| any | ✅ PASS |
| all | ✅ PASS |
| none | ✅ PASS |
| firstval | ✅ PASS |
| lastval | ✅ PASS |
| minmax | ✅ PASS |
| pairwise | ✅ PASS |
| first_index | ✅ PASS |
| last_index | ✅ PASS |

## 依赖

- Perl >= 5.42.0
- Module::Implementation >= 0.09（可选，用于 XS/PP 模式切换）

## 版本历史

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 0.59-r1 | built | 2026-06-12 | 纯 Perl 模式编译 |

## 参考

- CPAN: https://metacpan.org/pod/List::SomeUtils
- 源码: https://cpan.metacpan.org/authors/id/D/DR/DROLSKY/List-SomeUtils-0.59.tar.gz
