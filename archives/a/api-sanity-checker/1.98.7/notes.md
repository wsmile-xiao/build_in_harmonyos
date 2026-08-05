# api-sanity-checker 1.98.7 适配笔记

## 编译环境
- 构建系统: perl
- 编译日期: 2026-08-05
- 编译器: N/A（Perl 项目）
- 状态: published

## 编译步骤

api-sanity-checker 是一个纯 Perl 脚本工具，无需传统编译步骤。

### 安装流程

1. **下载源码**: 从 GitHub 下载 api-sanity-checker 1.98.7 版本
   ```bash
   curl -L https://github.com/lvc/api-sanity-checker/archive/refs/tags/1.98.7.tar.gz
   ```

2. **修改 shebang**: 适配 HarmonyOS Perl 路径
   ```bash
   # 通过 patch 修改 #!/usr/bin/perl → #!/usr/bin/env perl
   ```

3. **安装**: 直接在 conanfile.py 中执行等效 Makefile.pl 安装步骤
   - 读取 api-sanity-checker.pl，替换 MODULES_INSTALL_PATH
   - 写入 share/api-sanity-checker/api-sanity-checker.pl
   - 复制 modules/ 到 share/api-sanity-checker/modules/
   - 创建 bin/api-sanity-checker wrapper 脚本

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Perl 路径不对 | HarmonyOS Perl 不在 /usr/bin/perl | 修改 shebang 为 #!/usr/bin/env perl |
| 2 | Makefile.pl 兼容性 | Perl 5.42 下 File::Spec 导入和 Getopt::Long 单破折号选项有兼容性问题 | 直接在 conanfile.py 中执行等效安装步骤 |
| 3 | $0 路径解析 | 从 PATH 调用时 $0 无完整路径，getModules() 找不到 modules | 使用 wrapper 脚本解析路径调用真实脚本 |

## 源码修改

### 补丁文件: 0001-api-sanity-checker.pl.patch

修改 api-sanity-checker.pl 的 Perl shebang 路径：
- 原始: `#!/usr/bin/perl`
- 修改: `#!/usr/bin/env perl`

## 依赖版本

- Perl: 5.42.0
- abi-compliance-checker: 2.3（Conan 依赖）

## 验证结果

```bash
$ api-sanity-checker --version
API Sanity Checker 1.98.7
Copyright (C) 2015 Andrey Ponomarenko's ABI Laboratory
License: LGPL or GPL <http://www.gnu.org/licenses/>
This program is free software: you can redistribute it and/or modify it.

Written by Andrey Ponomarenko.
```

## 注意事项

1. **Perl 路径**: HarmonyOS Perl 通过 /usr/bin/env perl 查找
2. **安装方式**: 简单的文件复制，无编译过程
3. **Wrapper 脚本**: 解决 $0 路径解析问题
4. **依赖**: abi-compliance-checker/2.3 通过 Conan 依赖管理
