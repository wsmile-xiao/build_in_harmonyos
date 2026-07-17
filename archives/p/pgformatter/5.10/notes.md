# pgformatter 5.10 适配笔记

## 软件概述

pgFormatter（pg_format）是 PostgreSQL SQL 和 PL/PGSQL 语法美化/格式化工具，纯 Perl 实现，无需编译。

## 构建系统

- **类型**: makefile（Makefile.PL + ExtUtils::MakeMaker，纯 Perl，无 C/C++ 编译）
- **可执行文件**: `pg_format`，一个自包含 Perl 脚本
- **运行依赖**: Perl（HarmonyOS PC 系统预装 v5.42.x），仅使用核心模块 + 自带 `lib/pgFormatter/*`

## 适配说明

- pg_format 通过 `use FindBin; use lib "$FindBin::RealBin/lib";` 加载同级 `lib/` 目录中的
  `pgFormatter::Beautify` / `CLI` / `CGI` 模块。因此 `package()` 必须把 `pg_format` 复制到 `bin/`，
  并把 `lib/` 一并复制到 `bin/lib/`，保持脚本与模块的相对位置（`RealBin/lib`）。
- 原始 shebang 为 `#!/usr/bin/env perl`。OHOS 运行时 `/usr/bin/env` 未必可用，
  不能保留该 env shebang。但硬编码 `/usr/bin/perl` 也不可行——CI worker 上 perl 实际位于
  `/data/service/hnp/bin/perl` 等路径，写死会导致 "bad interpreter"。故在 `package()` 阶段
  **动态探测**构建机上的 perl 真实路径（`_get_perl()`：依次查 `$PERL` 环境变量、已知 OHOS 路径、
  `PATH`），用该路径替换 shebang；仅当完全探测不到时才回退到约定路径 `/usr/bin/perl`。
  参考 perl-sql-abstract 的同款探测逻辑。
- `settings` 仅需 `os` 和 `arch`（无编译器相关设置）。
- `package_type` 为 `application`（命令行工具）。
- 无补丁、无 Conan 依赖（Perl 视为系统预装）。

## 测试

- 上游测试基于 `make test`（t/01_lint.t 语法检查、t/02_regress.t 回归套件），依赖测试数据集，不适用于 Conan 测试环境。
- test_package 使用烟雾 + 功能测试：
  1. `pg_format --version` 验证可执行；
  2. 通过 stdin 格式化一条 SQL，校验输出中关键字被大写（默认行为），确认核心功能真实可用。

## 已知问题

- Perl 模块加载依赖 `bin/lib` 与 `pg_format` 的相对位置，打包时不可拆分二者。
