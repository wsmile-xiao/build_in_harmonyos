# tofrodos

DOS/Unix 文本格式转换工具，提供 `fromdos` 和 `todos` 命令用于转换文本文件的换行符格式。

## 功能

- `fromdos`: 将 DOS 格式（CRLF）转换为 Unix 格式（LF）
- `todos`: 将 Unix 格式（LF）转换为 DOS 格式（CRLF）

## 版本

- 1.8.3 (built)

## 构建说明

- 构建系统: Makefile (plain Makefile)
- 编译器: clang
- 特殊处理: Makefile 不支持 DESTDIR，需手动安装