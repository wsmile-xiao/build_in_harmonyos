# List::Compare

Perl 模块，用于比较两个或多个列表的元素。

## 描述

List::Compare 提供了一套丰富的列表比较功能，包括：
- 交集（intersection）
- 并集（union）
- 差集（difference）
- 补集（complement）
- 对称差集（symmetric difference）
- 子集检测
- 等价检测

## 已编译版本

| 版本 | 状态 | 编译日期 | 补丁 |
|------|------|---------|------|
| 0.55 | built | 2026-06-12 | 无 |

## 平台支持

- **鸿蒙 (aarch64-unknown-linux-ohos)**: ✅ 已验证可用

## 使用方法

```perl
use List::Compare;

# 创建比较对象
my $lc = List::Compare->new([1, 2, 3], [2, 3, 4]);

# 获取交集
my @intersection = $lc->get_intersection;  # [2, 3]

# 获取并集
my @union = $lc->get_union;  # [1, 2, 3, 4]

# 获取差集（只在第一个列表中）
my @unique = $lc->get_unique;  # [1]

# 获取补集（只在第二个列表中）
my @complement = $lc->get_complement;  # [4]

# 获取对称差集
my @symdiff = $lc->get_symmetric_difference;  # [1, 4]

# 子集检测
my $is_subset = $lc->is_LsubsetR;

# 等价检测
my $is_equivalent = $lc->is_LequivalentR;
```

## 特点

- 纯 Perl 模块，无需编译器
- 支持多列表比较
- 支持哈希键比较
- 提供面向对象和功能式两种接口

## 注意事项

- 用户需设置 PERL5LIB 环境变量：
  ```bash
  export PERL5LIB="/path/to/lib/site_perl/5.42.0:/path/to/lib/5.42.0"
  ```