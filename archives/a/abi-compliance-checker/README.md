# abi-compliance-checker

ABI Compliance Checker — A tool for checking backward API/ABI compatibility of C/C++ shared libraries.

## 简介

abi-compliance-checker 是一个用于分析 C/C++ 共享库 ABI 兼容性的工具。它能够比较两个版本的库，检测 ABI 变更（如函数签名变化、符号删除等）。

## 版本

- 当前编译版本: 2.3

## 依赖

- Perl 5 (≥ 5.8)

## 安装

通过 Conan 安装：
```bash
conan install --requires=abi-compliance-checker/2.3 -r=ohpcd
```

## 平台适配说明

### HarmonyOS 适配

1. **Perl 路径**: HarmonyOS Perl 不在标准路径 `/usr/bin/perl`，使用 `#!/usr/bin/env perl` 适配
2. **安装方式**: 纯 Perl 脚本，通过 Makefile.pl 安装（复制脚本和模块）

## 编译状态

- 2.3: published ✅
