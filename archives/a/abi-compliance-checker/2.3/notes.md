# abi-compliance-checker 2.3 适配笔记

## 编译环境
- 构建系统: perl
- 编译日期: 2026-08-05
- 编译器: N/A（Perl 项目）
- 状态: published

## 编译步骤

abi-compliance-checker 是一个纯 Perl 脚本工具，无需传统编译步骤。

### 安装流程

1. **下载源码**: 从 GitHub 下载 abi-compliance-checker 2.3 版本
   ```bash
   curl -L https://github.com/lvc/abi-compliance-checker/archive/refs/tags/2.3.tar.gz
   ```

2. **修改 shebang**: 适配 HarmonyOS Perl 路径
   ```bash
   # 通过 patch 修改 #!/usr/bin/perl → #!/usr/bin/env perl
   ```

3. **安装**: 使用 Perl Makefile.pl 安装脚本
   ```bash
   perl Makefile.pl -install -destdir=<install_dir> -prefix=/usr
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Perl 路径不对 | HarmonyOS Perl 不在 /usr/bin/perl | 修改 shebang 为 #!/usr/bin/env perl |

## 源码修改

### 补丁文件: 0001-shebang-fix.patch

修改 abi-compliance-checker.pl 的 Perl shebang 路径：
- 原始: `#!/usr/bin/perl`
- 修改: `#!/usr/bin/env perl`

## 依赖版本

- Perl: 5.42.0

## 验证结果

```bash
$ abi-compliance-checker --version
ABI Compliance Checker 2.3
Copyright (C) 2018 Andrey Ponomarenko's ABI Laboratory
...
```

## 注意事项

1. **Perl 路径**: HarmonyOS Perl 通过 /usr/bin/env perl 查找
2. **安装方式**: 简单的文件复制，无编译过程
3. **DESTDIR模式**: 使用 DESTDIR + prefix 安装以生成相对模块路径
