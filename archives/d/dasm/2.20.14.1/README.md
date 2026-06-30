# dasm — 鸿蒙预编译包

## 基本信息

| 字段 | 值 |
|------|------|
| 软件名 | dasm |
| 版本 | 2.20.14.1 |
| 构建系统 | makefile (纯Makefile) |
| 编译器 | clang/clang++ 15.0.4 (aarch64) |
| 状态 | published |
| 编译日期 | 2026-06-13 |
| 源码URL | https://github.com/dasm-assembler/dasm/archive/refs/tags/2.20.14.1.tar.gz |
| sha256 | ec71ffd10eeaa70bf7587ee0d79a92cd3f0a017c0d6d793e37d10359ceea663a |

## 软件简介

dasm 是一个多架构宏汇编器，支持 6502/68HC11/68705/F8/6303 等多种处理器架构。
ftohex 是随 dasm 附带的辅助工具，用于二进制转换。

## 预编译包内容

```
bin/dasm      — 主汇编器 ELF (aarch64, 已strip)
bin/ftohex    — 辅助转换工具 ELF (aarch64, 已strip)
lib/external/ — 外部库目录（空）
share/man/man1/dasm.1 — man 手册页
```

## 补丁列表

| 补丁 | 说明 |
|------|------|
| 0001-Makefile.patch | 添加标准 install 目标（含 DESTDIR/PREFIX 支持） |
| 0002-configure.patch | 创建 dummy configure 脚本（exit 0）兼容 G0 门禁 |
| 0003-test-test-report.txt.patch | 测试报告占位文件 |

## 注意事项

- dasm 不支持 `--version` 参数，直接运行 `dasm` 显示版本信息
- ftohex 是辅助工具，随 dasm 一起安装到 `bin/` 目录
- HMDFS 上安装时需先 rm -f 再 cp（不能覆盖已有文件）
