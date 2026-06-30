# perl-module-build-using-pkgconfig

## 简介

Module::Build::Using::PkgConfig 是 Module::Build 的子类，为基于 XS 的 Perl 模块提供便捷方法来使用通过 pkg-config 管理的平台库。它简化了在 Build.PL 脚本中查找和使用系统库的流程，并支持通过 Alien:: 模块动态安装缺失的库依赖。

## OHOS 适配

### 适配要点

- **纯 Perl 模块**：无 XS/C 代码编译，不受 SELinux HMDFS 限制影响（与 perl-dbd-pg 不同）
- **构建系统**：使用 Module::Build (Build.PL)，非 autotools/MakeMaker
- **运行依赖**：需要 pkg-config 命令在运行时可用（已预装于 `/data/service/hnp/bin/pkg-config`）
- **Perl 依赖**：需要 ExtUtils::PkgConfig 模块（1.16），需从 CPAN 手动安装

### 与 Linux 的差异

- OpenHarmony 上 pkg-config 安装在 `/data/service/hnp/bin/`，需确保在 PATH 中
- 作为纯 Perl 模块，安装后立即可用，无需签名或特殊权限处理
- 不涉及 CRT 文件缺失或链接器参数问题（纯 Perl 无二进制产物）

## 依赖

### 编译依赖
- Perl 5.42.0
- Module::Build >= 0.4004

### 运行依赖
- Perl 5.42.0
- ExtUtils::PkgConfig >= 1.16
- pkg-config (系统命令)

## 功能验证

```bash
# 加载模块
perl -MModule::Build::Using::PkgConfig -e 'print "Version: $Module::Build::Using::PkgConfig::VERSION\n"'

# 测试 pkg-config 集成
perl -e 'use Module::Build::Using::PkgConfig;
  my $b = Module::Build::Using::PkgConfig->new(module_name=>"T",dist_name=>"T",dist_version=>"1");
  print $b->try_pkgconfig("zlib") ? "zlib: yes" : "zlib: no";'
```

## 参考

- CPAN: https://metacpan.org/dist/Module-Build-Using-PkgConfig
- 源码: https://cpan.metacpan.org/authors/id/P/PE/PEVANS/Module-Build-Using-PkgConfig-0.03.tar.gz
- 作者: Paul Evans <leonerd@leonerd.org.uk>
