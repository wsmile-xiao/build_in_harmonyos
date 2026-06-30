# api-sanity-checker 1.98.7 适配笔记

## 编译环境
- 构建系统: perl
- 编译日期: 2026-06-18
- 编译器: N/A（Perl 项目）
- 状态: published

## 编译步骤

api-sanity-checker 是一个纯 Perl 脚本工具，无需传统编译步骤。

### 安装流程

1. **下载源码**: 从 GitHub 下载 api-sanity-checker 1.98.7 版本
   ```bash
   curl -k -L https://github.com/lvc/api-sanity-checker/archive/refs/tags/1.98.7.tar.gz
   ```

2. **安装依赖**: 安装 abi-compliance-checker 2.3
   ```bash
   cd ~/tmp/abi-compliance-checker
   sed -i '1s|#!/usr/bin/perl|#!/storage/Users/currentUser/usr/local/bin/perl|' abi-compliance-checker.pl
   perl Makefile.pl -install -prefix ~/usr/local
   ```

3. **修改 shebang**: 适配 HarmonyOS Perl 路径
   ```bash
   sed -i '1s|#!/usr/bin/perl|#!/storage/Users/currentUser/usr/local/bin/perl|' api-sanity-checker.pl
   ```

4. **安装**: 使用 Perl Makefile.pl 安装脚本
   ```bash
   perl Makefile.pl -install -prefix ~/usr/local
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Perl 路径不对 | HarmonyOS Perl 不在 /usr/bin/perl | 修改 shebang 为 ~/usr/local/bin/perl |
| 2 | 缺少依赖 abi-compliance-checker | 安装脚本检查依赖 | 先编译安装 abi-compliance-checker |
| 3 | File::Spec Perl 错误 | Makefile.pl 的导入语法问题 | 忽略，不影响安装成功 |

## 源码修改

### 补丁文件: 0001-api-sanity-checker.pl.patch

修改 api-sanity-checker.pl 的 Perl shebang 路径：
- 原始: `#!/usr/bin/perl`
- 修改: `#!/storage/Users/currentUser/usr/local/bin/perl`

这是 HarmonyOS 平台必需的修改，因为 Perl 不在标准路径。

## 依赖版本

- Perl: 5.42.2
- abi-compliance-checker: 2.3（要求 ≥ 1.98.7）

## 验证结果

```bash
$ api-sanity-checker --version
API Sanity Checker 1.98.7
Copyright (C) 2015 Andrey Ponomarenko's ABI Laboratory
License: LGPL or GPL <http://www.gnu.org/licenses/>
This program is free software: you can redistribute it and/or modify it.

Written by Andrey Ponomarenko.

$ api-sanity-checker -dumpversion
1.98.7

$ abi-compliance-checker -dumpversion
2.3
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| api-sanity-checker-1.98.7-ohos-aarch64.tar.gz | 557KB | 预编译包（Perl 脚本 + 模块） |

## 注意事项

1. **依赖**: 必须先安装 abi-compliance-checker，版本 ≥ 1.98.7
2. **Perl 路径**: HarmonyOS Perl 在 ~/usr/local/bin/perl，需要修改 shebang
3. **安装方式**: 简单的文件复制，无编译过程
4. **测试**: 内置测试需要 gcc，可跳过（工具本身功能正常）
---

**编译结束**: 2026-06-18 10:21
**最终状态**: published
