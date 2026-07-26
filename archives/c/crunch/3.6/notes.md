# crunch 3.6 适配笔记

## 编译环境
- 构建系统: makefile（上游 Makefile 直接编译 crunch.c，无 configure 步骤）
- 编译日期: 2026-07-16
- 编译器: clang（由 Conan conf `tools.build:compiler_executables:c` 注入，R33）
- 状态: built

## 源码

- 官方源: https://github.com/crunchsec/crunch/archive/refs/heads/master.tar.gz
- sha256: `c9498c90c9d8f9dd505dcbdad8d7b8498be8cd79238a37deee83a25f0d1dc8bd`
- 说明: crunch 上游无版本 tag/Release，master 分支即 3.6 版本（VERSION 硬编码在 Makefile 中）

## 上游构建系统分析

crunch 上游为**简单 Makefile** 项目：

- 只有 `crunch.c` 一个源文件
- `Makefile` 直接调用 `$(CC) $(CPPFLAGS) $(CFLAGS_STD) $(CFLAGS) $(LFS) crunch.c $(LIBFLAGS) $(LDFLAGS) -o crunch`
- 链接库: `-lm -pthread`
- 无 configure 步骤，无 config.h 生成
- 无 `make check` / 测试套件

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无版本 tag | 上游仅维护 master 分支，无 git tag/release | 使用 `master.tar.gz`，VERSION 3.6 硬编码在 Makefile 中 |
| 2 | 上游 Makefile 依赖 `gcc`（硬编码） | `CC = $(shell which gcc)` | 配方中直接调用 clang，通过 Conan conf 注入（R33） |
| 3 | test_package 中 mktemp /tmp 失败 | OHOS 的 /tmp 为只读（E002） | 改用 `mktemp -p "${TMPDIR:-/tmp}"`，利用 $TMPDIR 环境变量 |

## 编译步骤（配方 build() 实际执行）

```bash
clang -Wall -pedantic -std=c99 -pthread crunch.c -lm -o crunch
```

## 源码修改

无补丁。crunch 3.6 为纯 C99 POSIX 代码，仅依赖 libm 和 pthread，OHOS 均提供，无需修改。

## 依赖版本

无外部依赖，仅 libc + libm + pthread。

## 验证结果

- test_package 先探测二进制能否在本平台启动；可启动则运行 `crunch 2 2 ab` 生成 4 个单词（aa, ab, ba, bb），验证行数和内容；
- 当平台拒绝执行未签名 ELF 时回退到 ELF 魔数校验。

## 注意事项

- crunch 为命令行工具（application 类型），已在软件级目录提供 commands.json (R38)。