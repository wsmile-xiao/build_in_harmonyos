# perl-module-runtime

## 软件描述

Module::Runtime - Perl 运行时模块处理工具

提供在运行时加载和管理 Perl 模块的函数，包括：
- `use_module()` - 加载模块并调用 import
- `require_module()` - 加载模块（不调用 import）
- `use_package_optimistically()` - 乐观加载模块
- `is_module_name()` / `check_module_name()` - 模块名验证
- `module_notional_filename()` - 生成模块文件名

## 版本历史

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 0.018 | published | 2026-06-18 | 纯 Perl 模块，365 测试全部通过 |

## 使用说明

### 安装

```bash
# 通过 cmd-pkgs 预编译包安装（推荐）
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- perl-module-runtime 0.018
```

### 验证

```perl
use Module::Runtime qw(use_module);
my $mod = use_module("Cwd");
print $mod->getcwd(), "\n";
```

### 平台兼容性

- ✅ OpenHarmony (aarch64) - 完全兼容
- 纯 Perl 模块，不受 SELinux HMDFS 限制
- 不需要 ELF 签名或 HNP 安装

## 依赖

- Perl >= 5.6
- ExtUtils::MakeMaker（编译时）

## 许可证

Perl 5 (Artistic 1.0 或 GPL 1.0)
