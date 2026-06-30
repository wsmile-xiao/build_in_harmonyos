# Menlo-Legacy 1.9022 适配笔记

## 编译环境
- 构建系统: Perl ExtUtils::MakeMaker (Makefile.PL)
- 编译日期: 2026-06-17
- 编译器: N/A（纯 Perl 模块）
- Perl 版本: 5.42.0 (aarch64-linux)
- 状态: built（质量门禁全部通过，可升级为 published）

## 软件概述

Menlo-Legacy 1.9022 是 cpanminus (App::cpanminus) 的遗留兼容模块，包含：
- `Menlo::Legacy` — 版本存根模块，定义 $VERSION = '1.9022'
- `Menlo::CLI::Compat` — cpanm 经典版本内部和客户端行为兼容层

该模块为 **纯 Perl 实现**，不含任何 XS/C 编译组件。

## 编译步骤

```bash
# 标准 Perl 模块编译流程
cd $BUILD_SRC_DIR
perl Makefile.PL
make
make test        # PASS
make install DESTDIR=$TEST_PREFIX   # staging 安装
make install     # 安装到 ~/usr/local
```

无需任何 configure 参数或源码修改，标准 `perl Makefile.PL && make && make install` 即可。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Menlo::CLI::Compat 加载失败 | 缺少传递依赖 Class::Tiny、File::Which、String::ShellQuote | 从 CPAN 下载编译安装（INSTALL_BASE=~/usr/local） |

## 源码修改

无补丁。源码 0 修改，edit-tracker 为空。

## 依赖版本

| 依赖 | 版本 | 类型 |
|------|------|------|
| Menlo | 1.9019 | 运行时（已安装） |
| version | 0.9933 | 运行时（系统自带） |
| ExtUtils::MakeMaker | ≥6.63_03 | 构建时（系统自带） |
| Class::Tiny | 1.008 | 传递依赖（需额外安装） |
| File::Which | 1.27 | 传递依赖（需额外安装） |
| String::ShellQuote | 1.04 | 传递依赖（需额外安装） |

## 验证结果

```bash
$ make test
t/basic.t .............. ok
All tests successful. Files=2, Tests=1. Result: PASS

$ perl -MMenlo::Legacy -e 'print Menlo::Legacy->VERSION'
1.9022

$ perl -MMenlo::CLI::Compat -e 'my $o = Menlo::CLI::Compat->new; print ref($o)'
Menlo::CLI::Compat
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| Menlo-Legacy-1.9022-ohos-aarch64.tar.gz | 96KB | 预编译包（纯 Perl 模块文件） |

## 与 perl-dbd-pg 编译经验对比

| 维度 | perl-dbd-pg 3.18.0 | Menlo-Legacy 1.9022 |
|------|--------------------|--------------------|
| 模块类型 | XS (C) + Pure Perl | 纯 Perl |
| SELinux 限制 | XS 模块无法从 HMDFS 加载 | 不受限制 |
| 补丁需求 | 2 个补丁（Makefile + Makefile.PL） | 无 |
| CRT 缺失处理 | 需 `-nostartfiles -nodefaultlibs -lc` | 不涉及 |
| HNP 安装 | 需要（系统目录安装+签名） | 不需要 |

**关键发现**: 纯 Perl 模块在 OpenHarmony 平台上不存在 perl-dbd-pg 遇到的 SELinux HMDFS 限制。Menlo-Legacy 可直接从 `~/usr/local/lib/site_perl/` 加载，无需特殊处理。

## 注意事项

1. **传递依赖**: `Menlo::CLI::Compat` 的完整功能依赖 Class::Tiny、File::Which、String::ShellQuote，这些是 Menlo 核心模块的传递依赖，非 Menlo-Legacy 自身声明
2. **打包建议**: 发布到 cmd-pkgs 时建议同时提供 Class-Tiny、File-Which、String-ShellQuote 的预编译包
3. **安装路径**: 纯 Perl 模块安装到 `~/usr/local/lib/site_perl/5.42.0/`，通过 HMDFS 可正常加载

---

**编译结束**: 2026-06-17 17:55
**最终状态**: built（质量门禁 G1-G4 全部 PASS，可升级为 published）
