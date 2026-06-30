# List::MoreUtils::XS

## 简介

List::MoreUtils::XS 是 Perl 的高性能列表处理模块，提供 `any`、`all`、`none`、`uniq`、`minmax` 等实用函数的 XS 实现（C 语言加速版本）。

主要功能：
- 判断函数：`any`、`all`、`none`、`notall`
- 计数函数：`true`、`false`
- 查找函数：`firstidx`、`lastidx`、`firstval`、`lastval`
- 排序函数：`minmax`、`bsearch`
- 集合函数：`uniq`、`duplicates`、`frequency`
- 数组操作：`pairwise`、`mesh`、`part`

## OHOS 适配

### 编译适配要点

1. **构建系统**: Perl XS 模块，使用 `perl Makefile.PL` 构建
2. **链接参数**: 需要添加 `OTHERLDFLAGS="-nostartfiles -nodefaultlibs"` 解决 CRT 文件缺失问题
3. **编译器检测**: Config::AutoConf::LMU 无法在 OpenHarmony 上正确检测，需要跳过检测并手动生成 `LMUconfig.h`

### 运行时限制

⚠️ **重要**: OpenHarmony SELinux 策略禁止在 HMDFS 文件系统上加载动态库。用户目录（`/storage/Users/currentUser`）位于 HMDFS 上，因此编译的 XS 模块无法直接加载。

**解决方案**:
```bash
# 方案 1: 使用 hnp 安装（推荐）
hnp install perl-list-moreutils-xs

# 方案 2: 手动安装到系统 Perl 目录（需要 root 权限）
sudo cp XS.so /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/auto/List/MoreUtils/XS/
```

### 环境变量

编译时需设置：
```bash
export CPATH="/storage/Users/currentUser/usr/local/include"
export LIBRARY_PATH="/storage/Users/currentUser/usr/local/lib"
```

## 依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| perl | 5.42.0 | 运行时 |
| musl | 1.2.5 | C 标准库 |

## 功能验证

安装到系统目录后：
```perl
use List::MoreUtils::XS qw(any all uniq minmax);
print "any: ", (any { $_ > 5 } (1, 3, 5, 7, 9)) ? "OK" : "FAIL", "\n";
print "all: ", (all { $_ < 10 } (1, 2, 3, 4, 5)) ? "OK" : "FAIL", "\n";
print "uniq: ", join(",", uniq(1, 2, 2, 3, 3, 4)), "\n";
print "minmax: ", join(",", minmax(5, 1, 3, 9, 7)), "\n";
```

## 已知问题

1. **编译警告**: 约 1242 个 `-Wcompound-token-split-by-macro` 警告，这是 Perl XS 宏展开的正常现象，不影响功能
2. **HMDFS 加载限制**: 需安装到系统目录才能使用

## 参考

- CPAN: https://metacpan.org/pod/List::MoreUtils::XS
- 源码: https://download.savannah.nongnu.org/releases/perl-list-moreutils-xs/