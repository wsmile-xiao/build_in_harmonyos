# tofrodos

DOS 与 UNIX 文本文件格式转换工具，别名 tofromdos。

## 描述

tofrodos 是一个用于在 DOS (CRLF) 和 UNIX (LF) 文本格式之间转换的命令行工具。它提供以下命令：

- **fromdos** / **dos2unix**: 将 DOS 格式 (CRLF `\r\n`) 转换为 UNIX 格式 (LF `\n`)
- **todos** / **unix2dos**: 将 UNIX 格式 (LF `\n`) 转换为 DOS 格式 (CRLF `\r\n`)

程序根据执行时的文件名自动选择转换方向：名为 `fromdos` 或 `dos2unix` 时执行 DOS→UNIX 转换，名为 `todos` 或 `unix2dos` 时执行 UNIX→DOS 转换。

## 主要特性

- 支持管道模式 (stdin/stdout)
- 支持软链接文件转换（转换实际指向的文件）
- 支持 UTF-8 和 UTF-8 BOM 文件
- 备份功能 (-b 选项)
- 错误日志 (-l 选项)
- 强制转换只读文件 (-f 选项)
- 保持文件属主和时间戳 (-p 选项，需 root)

## 已编译版本

| 版本 | 状态 | 构建系统 | 编译器 | 日期 |
|------|------|---------|---------|------|
| 2.0.0 | published | makefile | clang | 2026-06-10 |

## 许可证

GPL-2.0-only

## 依赖

无外部依赖（仅动态链接 musl libc）

## 编译要点

- 构建系统为自定义 Makefile (`makefile.gcc`)，不支持 configure/cmake
- 编译命令: `make -f makefile.gcc CC=clang LD=clang CDEBUG="-fPIC -O2" all`
- 软链接创建需使用 `rm -f && ln -s`（HMDFS 平台限制）
- 测试参考数据需使用 `.orig` 目录（解压时 CRLF 行尾被去除）

## 来源

https://github.com/ChristopherHeng/tofrodos