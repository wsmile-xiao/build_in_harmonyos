# perl-package-anon

Package::Anon - Anonymous packages for Perl (XS module)

## 软件信息

- **官网**: https://metacpan.org/dist/Package-Anon
- **源码**: https://cpan.metacpan.org/authors/id/A/AU/AUGGY/Package-Anon-0.05.tar.gz
- **许可证**: Artistic-1.0-Perl OR GPL-1.0-or-later
- **分类**: perl
- **构建系统**: Perl ExtUtils::MakeMaker (Makefile.PL)

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 0.05-r16 | built | 2026-07-02 | 首次编译成功，Conan 配方完整 |

## 运行依赖

- perl (5.42.0, aarch64-linux)

## 编译依赖

- OHOS SDK 26.0.0.18 (提供 sysroot 和 LLVM lib)
- clang 15.0.4 (OHOS SDK 自带)

## 使用说明

Package::Anon 是一个 Perl XS 模块，提供匿名包（anonymous package）功能，可用于创建没有名称的 Perl 包，动态添加方法和属性。

### 安装

预编译包安装到 `/data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/` 目录。

HNP 安装包：`packaging/perl-package-anon.hnp`

### 注意事项

由于 SELinux HMDFS 限制，XS 模块需要安装到系统目录 `/data/service/hnp` 才能正常加载。

安装方法：
```bash
# 解压 HNP 包到系统目录
unzip perl-package-anon.hnp -d /data/service/hnp/perl.org/perl_5.42.0/

# 验证
perl -MPackage::Anon -e 'print "OK\n"'
```

### 示例代码

```perl
use Package::Anon;

my $stash = Package::Anon->new;
$stash->add_method(get_answer => sub { return 42 });

my $obj = $stash->bless({});
print $obj->get_answer();  # 输出: 42
```

---
*OpenHarmony 编译归档 · 2026-07-02*
