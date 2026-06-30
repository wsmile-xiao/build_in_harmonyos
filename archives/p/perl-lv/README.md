# LV (perl-lv)

## 简介

LV 是一个 Perl 模块，用于简化 lvalue 子程序的创建和使用。lvalue 子程序允许像赋值给变量一样赋值给函数返回值。

**版本**: 0.006
**许可证**: GPL-1.0-or-later 或 Artistic-1.0-Perl
**作者**: Toby Inkster (tobyink@cpan.org)

## 功能

- 提供简洁的语法创建 lvalue 子程序
- 支持三种后端实现：
  - `LV::Backend::Sentinel` - 基于 Sentinel 模块（需要 XS 支持）
  - `LV::Backend::Magic` - 基于 Variable::Magic 模块（需要 XS 支持）
  - `LV::Backend::Tie` - 基于 Perl tie 机制（纯 Perl，兼容性最好）

## OHOS 适配

### 适配要点

1. **纯 Perl 模块**：LV 是纯 Perl 代码，无需编译 XS 扩展，无二进制产物
2. **后端选择**：在鸿蒙平台上，Sentinel 和 Magic 后端不可用（需要 XS 支持），默认使用 Tie 后端
3. **路径配置**：需要设置 `PERL5LIB` 包含安装路径才能加载模块
4. **下载源**：推荐使用 CPAN MetaCPAN 镜像下载源码

### 使用示例

```perl
use LV qw( lvalue get set );

my $xxx;
sub xxx :lvalue {
    lvalue
        get { $xxx }
        set { $xxx = $_[0] }
}

xxx() = 42;
print xxx();  # 输出 42
```

### 已知问题

- Sentinel 和 Magic 后端需要 XS 扩展（Sentinel.pm、Variable::Magic），在鸿蒙平台不可用
- 只能使用 Tie 后端，性能较低但兼容性好
- Tie 后端使用 Perl tie 机制，在高频调用场景下性能不如 XS 后端
- Savannah Nongnu 下载源可能不可用，推荐使用 CPAN MetaCPAN 镜像

## 依赖

### 编译依赖
- perl >= 5.6

### 运行依赖
- perl >= 5.42.0（鸿蒙平台预装版本）
- Sub::Name（可选，用于命名匿名函数，改善堆栈跟踪）

## 安装方式

### 方法 1：使用预编译包（推荐）

```bash
# 使用 cmd-pkgs 公共安装脚本
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- perl-lv 0.006
```

### 方法 2：手动安装预编译包

```bash
# 下载预编译包
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/perl-lv-0.006-ohos-aarch64.tar.gz -o perl-lv-0.006-ohos-aarch64.tar.gz

# 解压到 Perl 安装目录
tar xzf perl-lv-0.006-ohos-aarch64.tar.gz -C /usr/local/lib/perl5/site_perl/5.42.0/
```

### 方法 3：从源码编译

```bash
# 下载源码（从 CPAN MetaCPAN 镜像）
curl -fsSL "https://cpan.metacpan.org/authors/id/T/TO/TOBYINK/LV-0.006.tar.gz" -o LV-0.006.tar.gz

# 验证 sha256
sha256sum LV-0.006.tar.gz
# 输出: fa88c2d4af0b1126d46401e6355a65496d033cfc2a6a944653011a638adfa75c

# 解压并编译
tar xzf LV-0.006.tar.gz
cd LV-0.006
perl Makefile.PL
make
make test
make install
```

## 功能验证

```bash
# 设置 PERL5LIB 后验证模块可用
PERL5LIB="/storage/Users/currentUser/usr/local/lib/perl5/site_perl_merge/5.42.0:$PERL5LIB" perl -MLV -e 'print "LV version: $LV::VERSION\n"; print "Implementation: ", LV->implementation, "\n";'

# 输出应为：
# LV version: 0.006
# Implementation: LV::Backend::Tie
```

### 完整功能测试

```perl
use LV qw( lvalue get set );

# 创建 lvalue 子程序
my $counter;
sub counter :lvalue {
    lvalue
        get { $counter }
        set { $counter = $_[0] }
}

# 测试读写
counter() = 10;          # 设置值
print counter();         # 输出: 10
counter() = counter() + 5;  # 增加值
print counter();         # 输出: 15
```

## 预编译包内容

| 文件 | 说明 |
|------|------|
| lib/site_perl/5.42.0/LV.pm | 主模块 (4.2KB) |
| lib/site_perl/5.42.0/LV/Backend/Tie.pm | Tie 后端 (746B) |
| lib/site_perl/5.42.0/LV/Backend/Magic.pm | Magic 后端 (651B) |
| lib/site_perl/5.42.0/LV/Backend/Sentinel.pm | Sentinel 后端 (429B) |

## 排除与替代

无需要排除的命令或组件。

## 参考

- CPAN: https://metacpan.org/release/LV
- 作者: Toby Inkster (tobyink@cpan.org)
- 源码下载: https://cpan.metacpan.org/authors/id/T/TO/TOBYINK/LV-0.006.tar.gz
- 许可证: GPL-1.0-or-later 或 Artistic-1.0-Perl