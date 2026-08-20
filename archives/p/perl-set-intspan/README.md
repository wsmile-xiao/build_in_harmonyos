# perl-set-intspan

Perl Set::IntSpan module — manages sets of integers, newsrc style.

## 软件信息

- **官网**: https://metacpan.org/release/Set-IntSpan
- **源码**: https://cpan.metacpan.org/authors/id/S/SW/SWMCD/Set-IntSpan-1.19.tar.gz
- **许可证**: unknown (CPAN license field)
- **分类**: perl-module
- **类型**: 纯 Perl 模块（无 XS/C 代码）

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 1.19-r5 | published | 2026-06-29 | 纯 Perl 模块，原生兼容鸿蒙，无需补丁 |

## 运行依赖

- perl (≥ 5.42.0)

## 编译依赖

- 无（纯 Perl 模块，仅需 perl 本身）

## 使用说明

Set::IntSpan 是一个纯 Perl 模块，用于管理整数集合（以 newsrc 风格的区间表示法）。支持集合运算（并集、交集、差集、补集）、成员检测、迭代、基数计算等功能。

### 安装

通过 Conan 安装：

```bash
conan install --requires=perl-set-intspan/1.19-r5@ohpcd/stable --build=perl-set-intspan/1.19-r5@ohpcd/stable
```

Conan 自动设置 `PERL5LIB` 环境变量，Perl 即可找到模块。

### 示例

```perl
use Set::IntSpan;

my $set = Set::IntSpan->new('1-10,20-25');
print $set->cardinality();  # 16
print $set->member(5);      # true
print $set->member(15);     # false

my $union = $set->union(Set::IntSpan->new('15-30'));
my $inter = $set->intersect(Set::IntSpan->new('5-20'));
```

### API 注意事项

- `insert($n)` / `remove($n)` 只接受单个整数参数
- 范围插入应使用 `union(Set::IntSpan->new("range"))`
- 所有集合运算返回新的 Set::IntSpan 对象

### 与 perl-dbd-pg 的对比

| 特性 | perl-set-intspan | perl-dbd-pg |
|------|-----------------|-------------|
| 模块类型 | 纯 Perl | XS (含 C 代码) |
| 需要补丁 | 否 | 是（CRT 链接修复） |
| CRT 文件问题 | 不适用 | 需要 `-nostartfiles -nodefaultlibs -lc` |
| SELinux 限制 | 不适用 | XS 动态库需安装到系统目录 |
| 构建系统 | ExtUtils::MakeMaker | ExtUtils::MakeMaker |
| 鸿蒙兼容性 | 原生兼容 | 需适配 |

---
*OpenHarmony 编译归档 · 2026-06-29*
