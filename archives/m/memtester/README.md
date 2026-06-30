# memtester

用户空间内存测试工具，用于检测内存子系统故障。

## 简介

memtester 是一个用于压力测试内存子系统的实用工具。它运行一系列内存测试来检测间歇性内存故障，这些故障在正常使用中可能不会出现，但可能导致系统不稳定。

## 主要特性

- 测试多种内存模式（随机值、XOR/SUB/MUL/DIV 比较、行走位等）
- 支持 64 位寻址
- 可运行多次测试循环
- POSIX 兼容
- 支持 mlock 锁定内存页

## 构建系统

- **类型**: makefile（djbdns 风格，使用 conf-cc/conf-ld 配置）
- **无 configure 脚本**: 编译配置通过 conf-cc 和 conf-ld 文件完成
- **编译器**: clang 15.0.4

## 安装文件

- `bin/memtester`: 内存测试二进制程序
- `man/man8/memtester.8.gz`: 手册页

## 版本 4.7.1

- 许可证: GNU GPL version 2 (only)
- 作者: Copyright (C) 2001-2024 Charles Cazabon

## 验证

```
memtester version 4.7.1 (64-bit)
pagesize is 4096
```

真实执行测试（1MB × 1 循环）：全部 18 项内存测试通过。