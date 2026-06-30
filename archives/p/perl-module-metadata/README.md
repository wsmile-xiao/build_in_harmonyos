# perl-module-metadata (Module::Metadata)

Gather package and POD information from perl module files.

## 软件信息

| 属性 | 值 |
|------|-----|
| CPAN 名称 | Module-Metadata |
| 许可证 | Perl 5 (GPL/Artistic) |
| 主页 | https://github.com/Perl-Toolchain-Gang/Module-Metadata |
| 仓库 | https://github.com/Perl-Toolchain-Gang/Module-Metadata.git |
| 构建系统 | ExtUtils::MakeMaker (Makefile.PL) |
| 模块类型 | 纯 Perl (无 XS/C) |

## 描述

Module::Metadata 是 Perl 核心工具链模块，用于从 Perl 模块文件 (.pm) 中收集包名、版本号和 POD 信息。它是 CPAN 客户端、Module::Build、Dist::Zilla、Module::Install 等工具的底层依赖。

## Versions

| Version | Status | Date |
|---------|--------|------|
| 1.000038 | published | 2026-06-18 |

## 运行时依赖

所有依赖均为 Perl 核心模块，随 Perl 5.42.0 预装：

- Carp, Encode, Fcntl, File::Find, File::Spec, version, strict, warnings

## 安装

```bash
# 通过预编译包安装（推荐）
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- perl-module-metadata 1.000038

# 验证安装
perl -MModule::Metadata -e 'print Module::Metadata->VERSION'
# 输出: 1.000038
```

## 平台兼容性

✅ 完全兼容 OpenHarmony (aarch64) 平台：
- 纯 Perl 模块，无需编译 C/XS 代码
- 不受 SELinux HMDFS 限制
- 测试套件全部通过 (9 文件 385 项)
- 即装即用，无需管理员权限
