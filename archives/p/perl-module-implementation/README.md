# perl-module-implementation

## 软件描述

Module::Implementation - 为模块加载多个可选底层实现之一（如 XS 或 PurePerl 实现）。

该模块抽象了选择多个底层实现的过程，可用于提供模块的 XS 和纯 Perl 实现，或为特定操作系统加载实现。当知道所有实现并需要自动选择时使用。

## 版本历史

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 0.09 | published | 2026-06-18 | 纯 Perl 模块，编译无平台适配问题 |

## 使用说明

### 安装

```bash
# 通过预编译包安装
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- perl-module-implementation 0.09
```

### 验证

```bash
perl -MModule::Implementation -e 'print "Version: $Module::Implementation::VERSION\n"'
# 预期输出: Version: 0.09
```

### 依赖

- Perl 5.42.0+
- Module::Runtime 0.012+
- Try::Tiny
- Carp (Perl 核心模块)

### 注意事项

- taint 模式下需显式 `-I` 指定安装路径（OpenHarmony taint 模式忽略 PERL5LIB）
- 纯 Perl 模块，不受 SELinux HMDFS 限制
- 无需任何平台适配补丁
