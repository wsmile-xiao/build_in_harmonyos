# pgformatter

> pgFormatter — PostgreSQL SQL 和 PL/PGSQL 语法美化工具

## 基本信息

| 项目 | 内容 |
|------|------|
| 上游版本 | 5.10 |
| 许可证 | PostgreSQL |
| 主页 | https://github.com/darold/pgFormatter |
| 源码 | https://github.com/darold/pgFormatter |
| 构建系统 | makefile（Makefile.PL / ExtUtils::MakeMaker，纯 Perl 脚本，无编译） |
| 依赖 | 无（运行时需要系统预装 Perl） |

## 描述

pgFormatter 是一个用于格式化和美化 PostgreSQL SQL 及 PL/PGSQL 代码的工具。可执行文件 `pg_format`
是自包含的 Perl 脚本，通过 `FindBin` 加载同级 `lib/` 目录中的 `pgFormatter::*` 模块，
支持从文件或标准输入读取 SQL 并输出规范化排版结果。

## 支持版本

| 版本 | 状态 | 构建系统 |
|------|------|---------|
| 5.10 | built | makefile |
