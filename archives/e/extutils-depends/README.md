# ExtUtils::Depends

## 简介

ExtUtils::Depends 是一个 Perl 模块，用于简化 XS 扩展的构建过程，特别是那些依赖于其他 XS 扩展的模块。它提供了一种机制，让 XS 模块可以共享它们的头文件、typemap 和依赖信息。

## 功能特性

- **依赖管理**：自动加载和管理 XS 模块的依赖关系
- **typemap 合成**：合并来自多个依赖模块的 typemap
- **头文件共享**：收集和安装 C 头文件
- **WriteMakefile 辅助**：生成适合 ExtUtils::MakeMaker 的参数
- **Inline 支持**：提供 inheritable Inline 方法，支持 Inline::C 使用

## 主要用途

用于构建以下类型的 Perl XS 模块：
- Gtk2-Perl 系列（Gtk2, Glib, Gnome2::Canvas 等）
- 依赖其他 XS 模块的复杂 Perl 扩展
- 需要共享 C API 的 XS 模块

## 安装

### 通过预编译包安装（推荐）

使用 cmd-pkgs 公共安装脚本：

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- ExtUtils-Depends 0.8002
```

### 手动安装

将预编译包解压到 Perl 的 lib 目录：

```bash
tar xzf ExtUtils-Depends-0.8002-ohos-aarch64.tar.gz -C ~/usr/local
```

## 使用示例

```perl
use ExtUtils::Depends;

# 创建一个新的 Depends 对象
my $package = ExtUtils::Depends->new('My::XS::Module', 'Dependent::Module');

# 设置编译和链接参数
$package->set_inc("-I/opt/include");
$package->set_libs("-lmylib");

# 添加 XS 和 C 文件
$package->add_xs('myxs.xs');
$package->add_c('mycode.c');

# 添加 typemap
$package->add_typemaps('typemap');

# 保存配置信息
$package->save_config('Install/Files.pm');

# 获取 Makefile 参数
WriteMakefile(
    'NAME' => 'My::XS::Module',
    $package->get_makefile_vars()
);
```

## 验证

验证模块是否正确安装：

```perl
perl -e 'use ExtUtils::Depends; print "ExtUtils::Depends loaded successfully\n"'
```

## 鸿蒙适配说明

- 纯 Perl 模块，无 XS 代码
- 无特殊平台限制
- 无需 ELF 签名
- 可直接在用户目录加载和使用

## 依赖

- Perl 5.6 或更高版本
- ExtUtils::MakeMaker 7.44 或更高版本
- File::Spec
- Data::Dumper
- IO::File

## 许可证

Perl License（与 Perl 本身相同）

## 参考链接

- [MetaCPAN 文档](https://metacpan.org/pod/ExtUtils::Depends)
- [GitLab 仓库](https://gitlab.gnome.org/GNOME/perl-extutils-depends)
- [Gtk2-Perl 项目](http://gtk2-perl.sourceforge.net)