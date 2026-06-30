# bonnie++

文件系统和硬盘驱动器的基准测试套件 (Benchmark suite for file systems and hard drives)。

## 软件描述

Bonnie++ 是一组对硬盘和文件系统进行性能测试的工具。它执行多种简单测试，包括文件创建、读取、写入、删除和随机 I/O 性能。

## 当前版本: 2.00a

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| 2.00a | published ✅ | 2026-06-18 |

## 可执行文件

| 二进制文件 | 安装位置 | 说明 |
|-----------|----------|------|
| bonnie++ | sbin/ | 主文件系统基准测试 |
| zcav | sbin/ | 分区恒定角速度（磁盘读取基准） |
| getc_putc | sbin/ | 字符 I/O 基准测试 |
| getc_putc_helper | sbin/ | getc_putc 的辅助进程 |
| bon_csv2html | bin/ | CSV 转 HTML |
| generate_randfile | bin/ | 生成随机数据文件 |
| bon_csv2txt | bin/ | CSV 转文本（⚠️ Perl 脚本，需 Perl） |

## 构建配置

- **构建系统**: autotools
- **依赖**: 无（仅需 libc pthread）
- **编译器**: clang/clang++
- **配置参数**: `./configure --prefix=$DEFAULT_PREFIX`

## 应用的补丁

1. `0001-Makefile.patch` — install 目标添加 DESTDIR 支持 (R20)
2. `0002-Makefile.in.patch` — install 模板添加 DESTDIR 支持 (R20)
3. `0003-configure.patch` — umask 077 → 022，修复 HMDFS 权限问题 (E011)

## 功能测试摘要

所有核心二进制文件已在 OpenHarmony (aarch64) 平台上完成真实功能验证：
- bonnie++ 文件IO/元数据基准测试 ✅
- zcav 磁盘读取基准 (4117 MB/s) ✅
- getc_putc 字符I/O基准 (8种模式) ✅
- bon_csv2html CSV→HTML 转换 ✅
- generate_randfile 随机数据生成 ✅

详见 `2.00a/reports/test-report.md`。
