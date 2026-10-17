# perl-sql-statement

SQL::Statement — SQL 解析和执行引擎（纯 Perl 模块）

## 概述

SQL::Statement 提供 SQL 语句的解析、准备和执行能力，支持 SELECT/INSERT/UPDATE/DELETE 等 DML 语句，以及 CREATE/DROP 等 DDL 语句。包含 SQL::Parser（SQL 解析器）和 SQL::Eval（表达式求值）子模块。

## 版本

- **版本**: 1.414-r1
- **上游**: [SQL-Statement-1.414](https://metacpan.org/dist/SQL-Statement)
- **许可证**: GPL-1.0-or-later OR Artistic-1.0

## 构建系统

Perl ExtUtils::MakeMaker (Makefile.PL)

## 特点

- **纯 Perl 模块**：无 C/XS 编译，无链接依赖
- **无需补丁**：原生兼容鸿蒙平台
- **无需 CRT 文件**：与 perl-dbd-pg 等 XS 模块不同，不涉及 C 链接

## 运行时依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| Params::Util | 1.102 | 参数检查（XS，HMDFS 需 PP 模式） |
| Clone | 0.47 | 深拷贝 |
| Module::Runtime | 0.016 | 模块运行时加载 |
| Scalar::Util | (core) | 标量工具 |
| List::Util | (core) | 列表工具 |

## 鸿蒙平台注意事项

- Params::Util 包含 XS 组件(.so)，在 HMDFS 文件系统上加载受限
- 需设置环境变量 `PERL_PARAMS_UTIL_PP=1` 启用纯 Perl 模式
- Conan 配方通过 `runenv_info.define("PERL_PARAMS_UTIL_PP", "1")` 自动设置

## Conan 使用

```bash
conan install --requires=perl-sql-statement/1.414-r1@ohpcd/stable
```
