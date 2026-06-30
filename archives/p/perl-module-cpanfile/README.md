# perl-module-cpanfile

Module::CPANfile - parse and manage cpanfile dependencies for Perl modules.

## 描述

Module::CPANfile 是一个 Perl 模块，用于解析和管理 `cpanfile` 文件中的依赖声明。`cpanfile` 是一种声明式的依赖管理格式，广泛应用于 Perl 生态系统中。

## 版本

| 版本 | 状态 | 编译日期 |
|------|------|---------|
| 1.1004 | ✅ published | 2026-06-18 |

## 构建系统

- **类型**: perl-makemaker (ExtUtils::MakeMaker, Makefile.PL)
- **编译器**: 不需要 C 编译器（纯 Perl 模块）
- **平台**: OpenHarmony (aarch64-unknown-linux-ohos)

## 依赖

### 运行时依赖
- Perl >= 5.8.1（系统预装 Perl 5.42.0）
- CPAN::Meta >= 2.12091（系统自带）
- CPAN::Meta::Prereqs >= 2.12091（系统自带）
- parent（系统自带）

### 构建依赖
- ExtUtils::MakeMaker（系统自带）

## 安装

### 通过预编译包安装

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- perl-module-cpanfile 1.1004
```

### 手动安装

```bash
perl Makefile.PL INSTALL_BASE=~/usr/local
make
make test
make install
```

## 使用示例

```perl
use Module::CPANfile;

# 从 cpanfile 文件加载
my $file = Module::CPANfile->load("cpanfile");
my $prereqs = $file->prereqs;

# 获取 runtime 依赖
my $runtime = $prereqs->requirements_for('runtime', 'requires');
print "Perl: ", $runtime->requirements_for_module('perl'), "\n";

# 从字符串创建
my $file2 = Module::CPANfile->from_prereqs({
    runtime => { requires => { perl => '5.010', JSON => '2.0' } }
});
```

## 命令行工具

- `cpanfile-dump` - 从 cpanfile 中导出依赖列表
- `mymeta-cpanfile` - 从 MYMETA.json/META.json 生成 cpanfile

## 鸿蒙平台注意事项

- 纯 Perl 模块，无 C 代码编译，无 SELinux/HMDFS 限制
- 所有功能在鸿蒙平台上正常工作
- 已知限制: `merged_requirements` 方法因模块内部数据结构问题不可用（非平台特定）
