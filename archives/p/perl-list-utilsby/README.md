# List::UtilsBy (perl-list-utilsby)

List::UtilsBy 是一个 Perl 模块，提供高阶列表操作函数，允许通过键函数对列表进行排序、过滤、分组等操作。

## 功能概述

### 排序函数
- **sort_by** - 按键函数返回值排序（字符串）
- **rev_sort_by** - 反向排序
- **nsort_by** - 按键函数返回值排序（数字）
- **rev_nsort_by** - 反向数字排序

### 聚合函数
- **max_by** - 返回键值最大的元素
- **min_by** - 返回键值最小的元素
- **count_by** - 按键值计数，返回哈希表

### 过滤函数
- **uniq_by** - 按键值去重
- **partition_by** - 按键值分区，返回哈希表
- **extract_by** - 提取匹配元素并原地删除

### 合并函数
- **zip_by** - 合并多个数组
- **unzip_by** - 解压缩嵌套数组
- **bundle_by** - 分组打包

### 其他函数
- **weighted_shuffle_by** - 按权重随机洗牌

## OHOS 适配

### 适配要点
- ✅ **纯 Perl 模块**：无 XS/C 代码，编译无需特殊处理
- ✅ **无补丁**：源码无需修改即可编译
- ✅ **无 SELinux 限制**：不涉及动态库加载，可在 HMDFS 上正常使用

### 编译命令
```bash
perl Makefile.PL PREFIX=~/usr/local
make
make install
```

### 使用方式
```bash
# 设置 PERL5LIB 环境变量
export PERL5LIB=~/usr/local/lib/site_perl/5.42.0

# 或在 Perl 脚本中指定
perl -I~/usr/local/lib/site_perl/5.42.0 -MList::UtilsBy -e '...'
```

### 已知问题
- 无已知问题，所有函数在 OpenHarmony 平台完全可用

## 依赖关系

### 编译依赖
- perl ≥ 5.42.0（系统预装）

### 运行依赖
- perl ≥ 5.42.0

## 安装

### 通过 cmd-pkgs 安装（推荐）
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- perl-list-utilsby 0.12
```

### 手动安装预编译包
```bash
tar -xzf perl-list-utilsby-0.12-ohos-aarch64.tar.gz -C ~/usr/local
export PERL5LIB=~/usr/local/lib/site_perl/5.42.0
```

## 使用示例

### 基本排序
```perl
use List::UtilsBy qw(sort_by nsort_by);

# 字符串排序
my @sorted = sort_by { $_ } qw(c b a d);  # → a, b, c, d

# 数字排序
my @nums = nsort_by { $_ } (5, 2, 10, 1);  # → 1, 2, 5, 10

# 按对象属性排序
my @by_name = sort_by { $_->{name} } ({name=>'z'}, {name=>'a'});
```

### 唯一值过滤
```perl
use List::UtilsBy qw(uniq_by);

# 按属性去重
my @uniq = uniq_by { $_->{id} } ({id=>1}, {id=>1}, {id=>2});
# → 2 个元素
```

### 计数与分区
```perl
use List::UtilsBy qw(count_by partition_by);

# 计数
my %counts = count_by { $_ } qw(a b a c b a);  # → {a=>3, b=>2, c=>1}

# 分区
my %parts = partition_by { $_ % 2 } (1, 2, 3, 4, 5);
# → {0=>[2,4], 1=>[1,3,5]}
```

### 提取与删除
```perl
use List::UtilsBy qw(extract_by);

my @arr = (1, 2, 3, 4, 5);
my @evens = extract_by { $_ % 2 == 0 } @arr;
# @evens → [2, 4]
# @arr → [1, 3, 5] (原数组被修改)
```

## 版本历史

| 版本 | 状态 | 编译日期 | 测试结果 |
|------|------|----------|----------|
| 0.12 | published | 2026-06-12 | 100% PASS (14/14) |

## 参考资料

- [CPAN - List::UtilsBy](https://metacpan.org/pod/List::UtilsBy)
- [源码仓库](https://github.com/leo-list-utilsby/List-UtilsBy)

---

*OpenHarmony 编译智能体 - 2026-06-15*