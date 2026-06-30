# Math::BaseCnv

Perl模块，提供在不同进制（2-64或96）之间转换数字的功能。

## 概述

Math::BaseCnv 是一个纯 Perl 实现的数字进制转换模块，支持在任意进制之间进行转换。适用于需要处理不同进制数字表示的场景，如：

- 十进制 ↔ 二进制
- 十进制 ↔ 十六进制
- 十进制 ↔ 六十四进制
- 任意进制之间的相互转换

## 版本信息

- **当前版本**: 1.14
- **发布日期**: 2016-07-30
- **许可证**: GPL-3.0
- **作者**: Pip Stuart

## 安装

通过 cmd-pkgs 安装：

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- perl-math-basecnv 1.14
```

安装后模块位于 `~/usr/local/lib/site_perl/5.42.0/Math/BaseCnv.pm`

## 使用示例

### Perl API

```perl
#!/usr/bin/perl
use strict;
use warnings;
use Math::BaseCnv;

# 十进制转二进制
my $binary = cnv(63, 10, 2);
print "63 in binary: $binary\n";  # 输出: 111111

# 二进制转十六进制
my $hex = cnv('111111', 2, 16);
print "111111 in hex: $hex\n";    # 输出: 3F

# 十六进制转十进制
my $decimal = cnv('3F', 16, 10);
print "3F in decimal: $decimal\n"; # 输出: 63

# 默认行为：十进制 ↔ 十六进制
my $hex2 = cnv(255);      # 十进制转十六进制
my $dec2 = cnv('FF');     # 十六进制转十进制
```

### 命令行工具

安装后提供 `cnv` 命令行工具：

```bash
# 十进制转十六进制
cnv 255 10 16
# 输出: FF

# 十六进制转二进制
cnv FF 16 2
# 输出: 11111111

# 二进制转十进制
cnv 1010 2 10
# 输出: 10
```

## 依赖

### 运行时依赖
- Perl 5.42.0+
- Carp (核心模块)
- Math::BigInt (核心模块)
- Memoize (核心模块)

### 构建依赖
- ExtUtils::MakeMaker
- Test::More
- Test::Pod (可选)
- Test::Pod::Coverage (可选)

## 测试状态

- ✅ 31/31 核心测试通过
- ✅ 质量门禁全部通过
- ✅ 鸿蒙平台验证通过

## 技术细节

- **实现**: 纯 Perl，无 XS/C 代码
- **支持的进制范围**: 2-64（标准），最高支持 96
- **编码**: 标准 64 进制使用 A-Z, a-z, 0-9, +, / 字符集
- **性能**: 使用 Memoize 优化常用转换

## 相关链接

- [CPAN 页面](https://metacpan.org/pod/Math::BaseCnv)
- [源码仓库](https://cpan.metacpan.org/authors/id/P/PI/PIP/Math-BaseCnv-1.14.tgz)

## 许可证

GPL-3.0

## 鸿蒙平台备注

该模块为纯 Perl 实现，无平台相关代码，在鸿蒙平台上无需特殊适配即可正常使用。所有依赖均为 Perl 核心模块，已包含在鸿蒙 Perl 发行版中。