# perl-module-install-authorrequires

## 软件描述

`Module::Install::AuthorRequires` 是 Perl 的 Module::Install 构建系统扩展模块，用于声明仅在作者环境中生效的依赖关系。

通常模块有一些可选依赖（如测试模块），这些依赖对开发者有用但不是模块运行的必需品。本模块提供了 `author_requires` 命令，使这些依赖仅在作者环境中强制要求，且不会出现在生成的 META.yml 文件中。

## 版本历史

| 版本 | 发布日期 | 状态 | 说明 |
|------|---------|------|------|
| 0.02 | 2009-07-14 | published | 当前版本，OpenHarmony 编译成功 |
| 0.01 | 2009-07-03 | - | 初始版本 |

## 使用说明

### 安装

```bash
# 通过 cmd-pkgs 安装预编译包
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- perl-module-install-authorrequires 0.02
```

### 使用示例

在 Makefile.PL 中使用：

```perl
use inc::Module::Install;

name 'My-Module';
all_from 'lib/My/Module.pm';

# 声明仅作者环境需要的依赖
author_requires 'Test::Pod';
author_requires 'Test::Pod::Coverage' => '1.00';

WriteAll;
```

### 关键特性

- 纯 Perl 模块，无 XS/C 编译依赖
- 与 Module::Install 框架无缝集成
- 作者依赖不会出现在 META.yml 中
- 自动检测作者环境

## OpenHarmony 编译信息

- **构建系统**: Perl (Makefile.PL + Module::Install)
- **Perl 版本**: 5.42.0 (aarch64-linux)
- **编译器**: N/A (纯 Perl 模块，无需编译器)
- **平台适配**: 零适配，开箱即用
- **测试结果**: PASS (1/1 测试通过)
- **质量门禁**: PASS (G1-G4 全部通过)

## 依赖

### 运行时依赖
- Perl >= 5.8.0
- Module::Install (任意版本)

### 构建依赖
- Perl >= 5.8.0
- ExtUtils::MakeMaker >= 6.42

## 许可证

Perl (Artistic License 1.0 / GPL)

## 作者

Florian Ragwitz <rafl@debian.org>
