# clipsafe

## 软件描述

clipsafe 是一个 Password Safe 数据库的命令行接口工具，使用 Perl 编写。

## 版本信息

| 版本 | 状态 | 日期 |
|------|------|------|
| 1.1 | published | 2026-06-30 |

## 技术信息

- **语言**: Perl
- **构建系统**: 无（独立 Perl 脚本）
- **许可证**: GPL-2.0
- **主页**: https://waxandwane.org/clipsafe.html
- **源码**: https://waxandwane.org/download/clipsafe-1.1.tar.gz

## 依赖

### 运行时 Perl 模块
- FileHandle（核心模块）
- Term::Cap（核心模块，含 ANSI 回退）
- POSIX（核心模块）
- DateTime（CPAN 模块，已改为可选）

### 系统依赖
- perl >= 5.0

## 版本 1.1 适配说明

- 源码为独立 Perl 脚本，无构建系统，安装方式为直接复制到 bin 目录
- 修复 shebang：`#!/usr/bin/perl` → `#!/usr/bin/env perl`
- DateTime 模块改为可选（平台未安装）
- Term::Cap 添加 ANSI 转义码回退（平台无 termcap 文件）
- Conan 配方引用：`clipsafe/1.1@ohpcd/stable`
