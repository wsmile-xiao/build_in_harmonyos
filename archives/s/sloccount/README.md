# SLOCCount

## 软件简介

SLOCCount（Source Lines Of Code Count）是一个用于统计多种编程语言源代码行数的工具集。它能够自动识别源代码文件的语言类型，并准确计算物理源代码行数（SLOC）。

## 功能特性

- 支持 30+ 种编程语言的代码统计
- 自动识别文件语言类型
- 生成详细的统计报告
- 支持递归目录扫描
- 提供 POSIX 平台兼容性

## 支持的语言

Ada, Assembly, AWK, C/C++, COBOL, CSH, Expect, Fortran, Fortran90, Haskell, Java, Lisp, Makefile, Modula3, Objective-C, Pascal, Perl, PHP, Python, Ruby, Sed, Shell, SQL, Tcl, JSP, ML 等。

## 版本信息

| 版本 | 编译状态 | 发布日期 |
|------|----------|----------|
| 2.26 | built | 2026-06-05 |

## 编译说明

### 构建系统
- 简单 Makefile（非标准 autotools，无 configure 脚本）
- 需要修改 Makefile 以支持 DESTDIR 安装

### 编译依赖
- 无外部库依赖
- 编译工具：clang, make, flex（部分计数器需要）

### 补丁说明
- `0002-makefile.patch`: 添加 DESTDIR 支持，用于 staging 安装

## 许可证

GPL-2.0-or-later

## 官方网站

https://dwheeler.com/sloccount/