# perl-module-install-authortests

## 软件描述

Module::Install::AuthorTests 是 Module::Install 的一个插件扩展，用于指定仅在模块作者构建时运行的测试文件。它提供了 `author_tests` 和 `recursive_author_tests` 两个命令，允许开发者将额外的测试放在 `xt/` 目录中，这些测试只在作者模式下运行，而不会在普通安装时执行。

## 版本历史

| 版本 | 编译日期 | 状态 | 说明 |
|------|---------|------|------|
| 0.002 | 2026-06-18 | published | 纯 Perl 模块，OpenHarmony aarch64 平台编译成功 |

## 构建信息

- **构建系统**: Makefile.PL (Perl ExtUtils)
- **Perl 版本**: 5.42.0 (aarch64-linux, OpenHarmony)
- **编译器**: Clang 21.1.5 (Harmonybrew ohos-llvm)
- **依赖**: Module::Install 1.21

### 配置选项

```bash
perl Makefile.PL INSTALL_BASE=$DEFAULT_PREFIX
make
make test
make install
```

## 安装方法

### 通过预编译包安装

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- perl-module-install-authortests 0.002
```

### 验证安装

```bash
perl -MModule::Install::AuthorTests -e 'print "Version: $Module::Install::AuthorTests::VERSION\n"'
# 输出: Version: 0.002
```

## 使用说明

### 在 Makefile.PL 中使用

```perl
use inc::Module::Install;

name 'MyModule';
author_tests 'xt';  # 指定作者测试目录

WriteAll();
```

### 可用命令

- `author_tests('xt')` — 指定作者测试目录（非递归）
- `recursive_author_tests('xt')` — 递归查找作者测试

## 平台适配说明

本模块为纯 Perl 代码，不包含任何 XS/C 扩展，在 OpenHarmony 平台上无需特殊适配。与 perl-dbd-pg 等包含 XS 模块的软件不同，本模块不涉及 ELF 签名或 SELinux HMDFS 限制问题，可从用户目录直接加载使用。
