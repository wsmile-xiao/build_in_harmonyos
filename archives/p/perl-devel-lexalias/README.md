# Devel::LexAlias

Perl XS 模块，用于创建词法变量的别名。

## 描述

Devel::LexAlias 提供了创建词法变量别名的功能，允许在不同的作用域中访问同一个变量。这在某些高级 Perl 编程场景中非常有用，特别是调试和代码分析工具。

## 功能特性

- 创建词法变量的别名
- 支持不同作用域的变量访问
- 与 PadWalker 和 Devel::Caller 模块配合使用

## 编译版本

- **版本**: 0.05
- **编译日期**: 2026-06-11
- **构建系统**: Perl XS (ExtUtils::MakeMaker)
- **状态**: built

## 依赖

- Perl 5.42.0
- PadWalker 2.5
- Devel::Caller 2.07

## 平台兼容性

- **目标平台**: aarch64-unknown-linux-ohos
- **编译器**: clang 18.1.8
- **特殊配置**: 需要 `-nostartfiles -nodefaultlibs` 链接参数

## 使用限制

⚠️ **HarmonyOS Perl XS 模块限制**：
- **用户目录限制**：XS 模块（.so 文件）在 HMDFS 文件系统上无法加载，受 SELinux 安全策略保护
- **管理员安装**：需要管理员安装到系统 Perl 目录 `/data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/`
- **签名机制**：系统目录的文件可能已通过特殊签名机制，可以正常加载

## 正确安装方法（管理员权限）

⚠️ **重要**：此 Perl XS 模块必须由管理员安装到系统 Perl 目录才能使用，普通用户无法自行安装。

### 安装步骤

```bash
# 1. 下载预编译包
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/perl-devel-lexalias-0.05-ohos-aarch64.tar.gz | tar xzf -

# 2. 创建系统 Perl 目录（需要管理员权限）
sudo mkdir -p /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/auto/Devel/LexAlias
sudo mkdir -p /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/Devel

# 3. 安装 Devel::LexAlias 模块（需要管理员权限）
sudo cp lib/perl5/site_perl/5.42.0/aarch64-linux/auto/Devel/LexAlias/LexAlias.so \
    /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/auto/Devel/LexAlias/

sudo cp lib/perl5/site_perl/5.42.0/aarch64-linux/Devel/LexAlias.pm \
    /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/Devel/

# 4. 安装依赖模块（如果尚未安装）
# PadWalker（需要管理员权限）
sudo mkdir -p /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/auto/PadWalker
sudo cp ~/usr/local/lib/perl5/site_perl/5.42.0/aarch64-linux/auto/PadWalker/PadWalker.so \
    /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/auto/PadWalker/
sudo cp ~/usr/local/lib/perl5/site_perl/5.42.0/aarch64-linux/PadWalker.pm \
    /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/

# Devel::Caller（需要管理员权限）
sudo mkdir -p /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/auto/Devel/Caller
sudo cp ~/usr/local/lib/perl5/site_perl/5.42.0/aarch64-linux/auto/Devel/Caller/Caller.so \
    /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/auto/Devel/Caller/
sudo cp ~/usr/local/lib/perl5/site_perl/5.42.0/aarch64-linux/Devel/Caller.pm \
    /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/Devel/

# 5. 验证安装
perl -MDevel::LexAlias -e 'print $Devel::LexAlias::VERSION'
# 输出: 0.05（表示安装成功）
```

### 验证依赖模块

```bash
# 验证 PadWalker
perl -MPadWalker -e 'print $PadWalker::VERSION'
# 输出: 2.5

# 验证 Devel::Caller
perl -MDevel::Caller -e 'print $Devel::Caller::VERSION'
# 输出: 2.07
```

### 常见问题

**Q: 为什么普通用户无法安装？**
A: HarmonyOS SELinux 策略阻止 HMDFS 文件系统上的未签名动态库加载，只有系统目录（可能已签名）才能加载 XS 模块。

**Q: 如果没有管理员权限怎么办？**
A:请联系系统管理员协助安装，或寻找纯 Perl 实现的替代方案。

**Q: 安装后如何使用？**
A: 安装成功后，可以直接在 Perl 代码中使用：`use Devel::LexAlias;`

## 补丁文件

- 0001-Makefile.PL.patch: 添加 OpenHarmony 链接参数

## 源码信息

- **上游源码**: https://cpan.metacpan.org/authors/id/R/RC/RCLAMP/Devel-LexAlias-0.05.tar.gz
- **作者**: Richard Clamp <richardc@unixbeard.net>
- **许可证**: Perl License

## 参考资料

- [CPAN Devel::LexAlias](https://metacpan.org/pod/Devel::LexAlias)
- [Perl XS 编程指南](https://perldoc.perl.org/perlxs)