# perl-module-runtime-conflicts

## 软件描述

Module::Runtime::Conflicts — 为 Module::Runtime 提供冲突检测信息。

该模块基于 Dist::CheckConflicts 框架，声明 Module::Runtime 与其他模块（如 Moose、MooseX::NonMoose、Elasticsearch）的版本冲突关系。被 Moose::Conflicts 和 moose-outdated 工具调用，用于在模块升级时检测潜在的兼容性问题。

## 版本历史

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 0.003 | published | 2026-06-18 | 纯 Perl 模块，OpenHarmony 平台编译通过 |

## 使用说明

### 安装

通过预编译包安装：
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- perl-module-runtime-conflicts 0.003
```

### 验证

```bash
perl -MModule::Runtime::Conflicts -e 'print Module::Runtime::Conflicts->VERSION'
# 预期输出: 0.003
```

### 功能

```perl
use Module::Runtime::Conflicts;

# 检测冲突（无冲突时正常返回，有冲突时抛出异常）
Module::Runtime::Conflicts->check_conflicts;

# 获取冲突列表
my @conflicts = Module::Runtime::Conflicts->conflicts;
```

## 平台兼容性

- **架构**: aarch64 (OpenHarmony)
- **Perl 版本**: 5.42.0
- **模块类型**: 纯 Perl 模块（无 XS/C 代码）
- **SELinux**: 不受 HMDFS 限制影响
- **ELF 签名**: 不适用（无二进制文件）

## 依赖

| 依赖 | 版本 | 类型 |
|------|------|------|
| Perl | 5.42.0 | 运行时 |
| Dist::CheckConflicts | 0.11 | 运行时 |
| Module::Runtime | 0.018 | 运行时 |
| ExtUtils::MakeMaker | 7.76 | 构建 |

## 许可证

Perl 5 (Perl Artistic License 1.0 + GPL)
