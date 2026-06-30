# gperf 3.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-21
- 编译器: clang/clang++
- 状态: published

## 编译步骤

由于 HMDFS 文件系统限制，标准的 autotools configure 流程无法正常工作（heredoc 创建临时文件失败）。采用手动生成配置文件的方式完成编译：

1. 初始化编译环境：`python3 $SKILL_ROOT/scripts/ohc-run.py init-build gperf 3.1 --url=https://ftp.gnu.org/gnu/gperf/gperf-3.1.tar.gz`
2. 手动生成 Makefile 和 config.h（绕过 configure 的 heredoc 问题）
3. 编译 lib 目录：`cd lib && make`
4. 编译 src 目录：`cd src && make`
5. 安装到 staging：`make install DESTDIR=$TEST_PREFIX`
6. 测试：`cd tests && make check`
7. 本地安装：`make install`（不带 DESTDIR）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 失败：config.status 无法创建临时文件 | HMDFS 文件系统限制，heredoc 语法在临时目录中无法写入文件 | 使用 Python 手动解析 config.status 中的变量，生成 Makefile 和 config.h |
| 2 | 缺少 libgp.a 库文件 | lib 目录未编译 | 先编译 lib 目录生成静态库，再编译 src |

## 源码修改

**补丁数量**: 0

无平台特定源码修改。gperf 在 HMDFS 环境下使用手动生成的配置文件完成编译，
无需修改任何源代码文件。

**平台适配方法**: 手动生成 Makefile 和 config.h（因 HMDFS heredoc 限制）

**补丁清理记录** (2026-05-21):
- 删除了 31 个测试生成文件补丁（tests/*.out, tests/*inset.c）
- 这些补丁违反 R6 铁律（只改源文件不改生成文件）
- 实际源码无修改，所有生成的配置文件（Makefile, config.h）都是手动创建
- make check 的输出文件不应作为补丁保存

## 依赖版本

- 无依赖

## 验证结果

```bash
$ gperf --version
GNU gperf 3.1
Copyright (C) 1989-2017 Free Software Foundation, Inc.
License GPLv3+: GNU GPL version 3 or later <http://gnu.org/licenses/gpl.html>
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.
Written by Douglas C. Schmidt and Bruno Haible.

$ make check
# 所有测试通过，无错误
```

## 测试结果

- **测试总数**: 24
- **通过数量**: 24
- **失败数量**: 0
- **通过率**: 100%
- **测试时间**: 2026-05-21 11:03:34 CST
- **测试环境**: OpenHarmony, clang 15.0.4

### 警告说明
- Ada Predefined Words: 1 个哈希冲突警告（设计预期）
- test-4: 8 个哈希冲突警告（测试 -D 选项）
- SMTP Keywords: 6 个编译警告（deprecated-non-prototype，不影响功能）

所有警告均为非阻塞性，不影响 gperf 的核心功能。

**详细报告**: reports/test-report.md

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| gperf-3.1-ohos-aarch64.tar.gz | 117K | 预编译包（仅包含 bin/gperf） |

## 注意事项

**系统性问题（L1 平台真理）**：HMDFS 文件系统环境下，autotools 的 config.status 脚本使用 heredoc 创建临时文件时会失败，报错：
```
./config.status[659]: can't create ./confXXXXX/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

这影响了所有使用 autotools 构建系统的软件。解决方案：
1. 手动生成配置文件（Python 解析变量替换）
2. 或等待平台修复

**建议**：将此问题记录到知识图谱作为新的错误模式（建议编号：E080），以便其他软件编译时快速识别和解决。
---

**编译结束**: 2026-05-21 10:44
**最终状态**: published
