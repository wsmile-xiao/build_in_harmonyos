# atool homebrew 适配笔记

## 编译环境

- 构建系统：Autotools
- 编译日期：2026-07-15
- 编译器：N/A（Perl 脚本工具，无 C 编译）
- 状态：built

## 源码信息

- 版本：0.39.0（Homebrew 对应上游版本）
- 官方源码 URL：`https://download.savannah.gnu.org/releases/atool/atool-0.39.0.tar.gz`
- SHA256：`aaf60095884abb872e25f8e919a8a63d0dabaeca46faeba87d12812d6efc703b`

## 软件简介

atool 是一个用于管理多种文件档案格式（tar、tar+gzip、zip 等）的 Perl 脚本工具。
主要命令：
- `aunpack` — 从档案中提取文件（先提取到新目录避免文件散落）
- `apack` — 创建档案
- `als` — 列出档案内容
- `acat` — 提取文件到标准输出
- `adiff` — 比较两个档案
- `arepack` — 重新打包档案

atool 通过文件扩展名识别档案格式，调用外部程序（tar/gzip/bzip2/zip 等）处理档案。

## 依赖

| 依赖 | 类型 | 说明 |
|------|------|------|
| perl | 运行时 | atool 使用 Perl 编写，OHOS 位于 /data/service/hnp/bin/perl |
| tar/gzip/bzip2/zip 等 | 运行时 | atool 调用外部程序处理档案 |

无构建期依赖（Release tarball 已预生成 configure/Makefile.in）。

## 编译步骤

1. 使用官方发布 tarball 源码，校验 SHA256。
2. Autotools 标准流程：`./configure --prefix=... && make install`。
3. OHOS 适配：修复 configure 脚本的 sh shebang；Perl 路径通过 PERL 环境变量让 configure 替换 `@PERL@`；修复 HMDFS umask 077 限制（E129）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 脚本无法执行 | OHOS 无 /bin/sh，configure 使用 `#! /bin/sh` | replace_in_file 替换为 `#!/system/bin/sh` (E165) |
| 2 | Perl 脚本 shebang 错误 | atool 脚本模板使用 `#!@PERL@`，由 configure 替换为实际 perl 路径 | 仅设置 PERL 环境变量，configure 自动替换 `@PERL@`；不要用 replace_in_file 查找 `#!/usr/bin/perl`（.in 模板中不存在该模式，会抛 ConanException） |
| 3 | configure 找不到 perl | OHOS perl 不在标准 PATH 上 | 设置 `os.environ["PERL"] = "/data/service/hnp/bin/perl"` |
| 4 | `config.status: error: could not setup config files machinery` / `./confeiMDFp/subs1.awk: Permission denied` | HMDFS 文件系统始终给新目录加 setgid 位，`umask 077` 创建出 `drwx--S---`，所有者也无法在目录内写文件（E129） | 在 configure 和 configure 生成的 config.status 中用 `replace_in_file(strict=False)` 把 `umask 077` 替换为 `umask 022` |

## 测试说明

atool 上游自带测试套件（make check），但可能依赖 Perl 测试框架和外部压缩工具。
OHOS 环境可能缺少部分依赖，test_package 采用功能烟雾测试。

test_package 参考 Homebrew formula 的测试逻辑：
- 创建测试文件，用 `apack` 打包成 tar.gz 档案
- 用 `als` 列出档案内容，验证包含测试文件名
- 验证 `atool --version` 输出

## 知识积累

- Perl 脚本工具在 OHOS 上的适配模式：若模板用 `@PERL@` 占位符，仅设置 PERL 环境变量即可；不要对 .in 模板做 replace_in_file（找不到 `#!/usr/bin/perl` 会失败）
- atool 的 .in 脚本模板使用 `#!@PERL@`，configure 会替换为实际 perl 路径
- atool 是 noarch（架构无关）工具，所有产物均为 Perl 脚本和文本文件
- E129 HMDFS umask 077 陷阱：Autotools 项目在 OHOS 上几乎都会踩，conanfile.py 中需对 configure 和 config.status 都做 `umask 077 -> umask 022` 替换
- Windows 环境无法进行 OHOS aarch64 本地验证，status 标记为 built，待 CI 验证
