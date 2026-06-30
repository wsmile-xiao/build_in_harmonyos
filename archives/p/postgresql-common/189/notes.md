# postgresql-common 189 适配笔记

## 编译环境
- 构建系统: makefile (simple Makefile + manual install)
- 编译日期: 2026-06-10
- 编译器: N/A (Perl/shell scripts)
- 状态: built

## 编译步骤
postgresql-common 是 Perl/shell 的 Debian PG 集群管理器。无标准 autotools/cmake。

1. make — 仅生成 man pages
2. 手动安装 — 基于 debian .install 文件列表
3. 无 configure/install 步骤

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | /usr/bin/perl shebang 不存在 | OH Perl 路径不同 | #!/usr/bin/env perl |
| 2 | /bin/bash shebang 不存在 | OH bash 路径不同 | #!/usr/bin/env bash |
| 3 | PgCommon.pm 找不到 | @INC 不含安装路径 | use FindBin; use lib "$FindBin::RealBin/../share/perl5" |
| 4 | ls -v toybox 不支持 | GNU ls -v 无 | ls | sort -V |
| 5 | Makefile 无 install | Debian dh_install | 手动安装 |
| 6 | pg_config 冲突 | PG17 已有二进制 | 不覆盖 |

## 源码修改
12 patches: shebang+use lib+ls fix

## 验证结果
pg_lsclusters OK, pg_conftool OK, pg_wrapper OK, PgCommon.pm OK

## 交付物
postgresql-common-189-ohos-aarch64.tar.gz (765KB)
---

**编译结束**: 2026-06-10 22:21
**最终状态**: published
