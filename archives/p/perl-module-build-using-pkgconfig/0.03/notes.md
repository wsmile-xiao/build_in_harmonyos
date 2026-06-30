# perl-module-build-using-pkgconfig 0.03 适配笔记

## 编译环境
- 构建系统: Module::Build (Build.PL)
- 编译日期: 2026-06-18
- 编译器: N/A（纯 Perl 模块，无 C 编译）
- 状态: published

## 编译步骤

```bash
# 1. 下载源码
wget https://cpan.metacpan.org/authors/id/P/PE/PEVANS/Module-Build-Using-PkgConfig-0.03.tar.gz
tar xzf Module-Build-Using-PkgConfig-0.03.tar.gz
cd Module-Build-Using-PkgConfig-0.03

# 2. 安装依赖 ExtUtils::PkgConfig（默认未预装）
cpan ExtUtils::PkgConfig

# 3. 构建和测试
perl Build.PL --prefix=$DEFAULT_PREFIX
./Build
./Build test

# 4. 安装
./Build install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `Can't locate ExtUtils/PkgConfig.pm` | ExtUtils::PkgConfig 未预装于 OpenHarmony | 从 CPAN 安装 ExtUtils::PkgConfig 1.16（纯 Perl 模块） |
| 2 | `Test::Pod 1.00 required` (skipped) | Test::Pod 未安装 | 跳过 POD 测试，不影响功能 |

## 源码修改

无。本模块为纯 Perl 代码，无需任何平台适配补丁。

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| Perl | 5.42.0 | 系统预装 (/data/service/hnp/perl.org/perl_5.42.0) |
| Module::Build | 0.4234 | 系统预装 |
| ExtUtils::PkgConfig | 1.16 | CPAN 安装 |
| Test::More | 1.302210 | 系统预装 |
| pkg-config | 0.29.2 | 系统预装 (/data/service/hnp/bin/pkg-config) |

## 验证结果

```bash
# 模块加载
$ perl -MModule::Build::Using::PkgConfig -e 'print "Version: $Module::Build::Using::PkgConfig::VERSION\n"'
Version: 0.03

# 测试套件
$ ./Build test
t/00use.t .. ok
t/99pod.t .. skipped: Test::Pod 1.00 required for testing POD
All tests successful.
Files=2, Tests=1, 0 wallclock secs
Result: PASS

# 功能测试 - pkg-config 集成
$ perl -e 'use Module::Build::Using::PkgConfig;
  my $b = Module::Build::Using::PkgConfig->new(module_name=>"T",dist_name=>"T",dist_version=>"1");
  print $b->try_pkgconfig("zlib") ? "zlib: yes\n" : "zlib: no\n";'
Checking pkg-config zlib ... yes
Using zlib from pkg-config
zlib: yes
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| perl-module-build-using-pkgconfig-0.03-ohos-aarch64.tar.gz | 22KB | 预编译包 |

## 注意事项

- 本模块是**纯 Perl 模块**，不涉及 XS/C 编译，因此不存在 SELinux HMDFS 限制问题（参考 perl-dbd-pg 的 XS 模块限制）
- ExtUtils::PkgConfig 是运行时必需依赖，默认未预装，需从 CPAN 安装
- pkg-config 命令必须可用且在 PATH 中，本模块在运行时通过 ExtUtils::PkgConfig 调用 pkg-config
- 预编译包中只包含 .pm 文件和 .packlist，无二进制文件需要签名

---

**编译结束**: 2026-06-22
**最终状态**: published
