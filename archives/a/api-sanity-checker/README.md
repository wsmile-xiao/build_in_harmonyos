# api-sanity-checker

API Sanity Checker - C/C++ 库 API 单元测试自动生成工具

## 简介

api-sanity-checker 是一个自动生成 C/C++ 库 API 基本单元测试的工具。它通过分析头文件中的声明，能够为 API 中的每个函数生成合理的测试用例。

生成的测试质量足以检查简单用例中的关键错误。工具能够构建并执行生成的测试，检测崩溃、信号、非零返回码和程序挂起等问题。

## 版本

- 当前编译版本: 1.98.7
- 最新稳定版本: 1.98.8

## 依赖

- Perl 5 (≥ 5.8)
- abi-compliance-checker (≥ 1.98.7)
- G++
- GNU Binutils
- Ctags

## 使用方法

基本用法：
```bash
api-sanity-checker -lib NAME -d VERSION.xml -gen -build -run
```

VERSION.xml 是 XML 描述符：
```xml
<version>
    1.0
</version>

<headers>
    /path/to/headers/
</headers>

<libs>
    /path/to/libraries/
</libs>
```

## 安装

通过 cmd-pkgs 安装预编译包：
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- api-sanity-checker 1.98.7
```

## 平台适配说明

### HarmonyOS 适配

1. **Perl 路径**: HarmonyOS Perl 不在标准路径 `/usr/bin/perl`，需要修改 shebang
2. **依赖安装**: 需要先安装 abi-compliance-checker
3. **测试**: 内置测试需要 gcc，环境缺少时可跳过

## 编译状态

- 1.98.7: published ✅
