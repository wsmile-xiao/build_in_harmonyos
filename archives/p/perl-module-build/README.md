# perl-module-build

Module::Build — Perl 模块构建和安装系统。

## 描述

Module::Build 是 Perl 的模块构建系统，用于编译、测试和安装 Perl 模块。它是 `ExtUtils::MakeMaker` 的现代替代方案，使用 `Build.PL` 脚本代替传统的 `Makefile.PL`。

## 版本历史

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 0.4234 | built | 2026-06-12 | 纯 Perl 模块，无需补丁 |

## 使用说明

```bash
# 构建 Perl 模块
cd Your-Module
perl Build.PL
./Build
./Build test
./Build install
```
