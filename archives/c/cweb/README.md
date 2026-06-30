# CWEB — C/C++/Java 文学编程文档系统

## 简介

CWEB 是由 Silvio Levy 和 Donald E. Knuth 创建的文学编程（Literate Programming）文档系统，
改编自 Knuth 的 WEB（面向 Pascal）。它允许将文档（TeX 格式）和代码（C/C++）写在同一个源文件中。

主要包含两个工具：
- **ctangle**：从 CWEB 源文件（.w）中提取 C/C++ 代码，生成 .c 文件
- **cweave**：从 CWEB 源文件（.w）中提取 TeX 文档，生成 .tex 文件

## 依赖

无 — CWEB 是独立工具，不需要任何外部库依赖。

## OHOS 适配要点

- **构建系统**：简单 Makefile（非 autotools），需打补丁适配
- **关键修改**：
  - Makefile 补丁：DESTDIR → BINDIR，新增 PREFIX 和标准 DESTDIR 变量，支持 staging 安装
  - CFLAGS/LINKFLAGS 使用 `?= 覆盖语法`，默认值适配 OHOS（`-fPIC -O2` 和 `-fuse-ld=/data/service/hnp/bin/ld.bfd`）
  - Bootstrap 编译需在 ctangle 编译后执行 ELF 签名才能继续
  - MANEXT 从 `l` 改为 `1`（标准 man 页编号）
- **已知限制**：文件名长度有限制（约128字符），绝对路径可能触发 "Filename too long" 错误

## 安装文件

| 文件 | 说明 |
|------|------|
| bin/ctangle | CWEB 代码提取工具（86KB） |
| bin/cweave | CWEB 文档提取工具（154KB） |
| lib/cweb/c++lib.w | C++ 类型库源文件 |
| lib/cweb/iso_types.w | ISO 类型库源文件 |
| share/man/man1/cweb.1 | man 手册页 |
| share/texmf/tex/generic/cwebacromac.tex | TeX 宏文件（缩写） |
| share/texmf/tex/generic/cwebmac.tex | TeX 宏文件（主文件） |
| share/emacs/site-lisp/cweb.el | Emacs 编辑器模式