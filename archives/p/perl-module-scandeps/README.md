# perl-module-scandeps

## 软件描述

Module::ScanDeps - Perl 模块依赖递归扫描工具

递归扫描 Perl 程序，查找其使用的所有模块（包括间接依赖），主要用于：
- `pp` (Perl Packager) 依赖分析
- PAR 打包工具的依赖检测后端
- `scandeps.pl` 命令行工具

### 主要功能

- `scan_deps()` - 函数式接口，扫描文件列表的依赖
- `scan_line()` - 扫描单行 Perl 代码的依赖
- `Module::ScanDeps->new()` - OO 接口（App::Packer 兼容）
- `scandeps.pl` - 命令行工具，支持 `-B`(bundle)、`-R`(递归)、`-C`(缓存) 等选项
- `Module::ScanDeps::Cache` - 依赖缓存模块，加速重复扫描

### 依赖检测能力

- 正确识别 `.pm` 模块文件（type=module）
- 正确识别 `.so` 共享库/XS 模块（type=shared）
- 正确识别数据文件（type=data）
- 支持递归扫描和缓存

## 版本历史

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 1.37 | published | 2026-06-18 | 纯 Perl 模块，201 测试全部通过 |

## 使用说明

### 安装

```bash
# 通过 cmd-pkgs 预编译包安装（推荐）
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- perl-module-scandeps 1.37
```

### 验证

```perl
use Module::ScanDeps qw(scan_deps);
my $deps = scan_deps(files => ['script.pl'], recurse => 1);
print "Found ", scalar(keys %$deps), " dependencies\n";
```

### 命令行工具

```bash
# 扫描脚本依赖（仅非核心模块）
scandeps.pl script.pl

# 扫描所有依赖（包括核心模块）
scandeps.pl -B script.pl

# 从表达式扫描
scandeps.pl -B -e "use DBI; use File::Spec;"

# 递归扫描 + 缓存
scandeps.pl -R -C cache.txt script.pl
```

### 平台兼容性

- ✅ OpenHarmony (aarch64) - 完全兼容
- 纯 Perl 模块，不受 SELinux HMDFS 限制
- 不需要 ELF 签名或 HNP 安装
- 能正确检测系统 XS 模块（.so）的依赖关系

## 依赖

- Perl >= 5.6
- ExtUtils::MakeMaker（编译时）

## 许可证

Perl 5 (Artistic 1.0 或 GPL 1.0)
