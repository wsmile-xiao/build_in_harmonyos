# aescrypt 0.7 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-13
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. `./configure --prefix=/storage/Users/currentUser/usr/local`
2. `make -j1` — 编译生成 aescrypt、aesget、tobin 三个二进制
3. 手动创建 DESTDIR staging 目录并复制 aescrypt、aesget 到 `$TEST_PREFIX/$DEFAULT_PREFIX/bin/`
4. `make install` — 直接安装到 `$DEFAULT_PREFIX/bin/`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 链接时 duplicate symbol: ROUNDS | rijndael.h 中 `int ROUNDS;` 是 tentative definition，被 aescrypt.c 和 rijndael.c 同时包含导致两个目标文件都定义了 ROUNDS | 将 rijndael.h 中 `int ROUNDS;` 改为 `extern int ROUNDS;`，在 rijndael.c 中添加 `int ROUNDS;` 作为唯一定义 |
| 2 | Makefile install 不支持 DESTDIR | Makefile 使用 `cp aescrypt @prefix@/bin` 硬编码路径，不支持 DESTDIR | 手动创建 staging 目录并复制文件 |

## 源码修改

### rijndael.h
- `int ROUNDS;` → `extern int ROUNDS;` （修复 duplicate symbol）

### rijndael.c
- 在 `#include "rijndael.h"` 后添加 `int ROUNDS;` （提供唯一定义）

## 依赖版本

无外部依赖。仅依赖 C 标准库和 musl libc。

## 验证结果

```bash
$ /storage/Users/currentUser/usr/local/bin/aescrypt
Usage: /storage/Users/currentUser/usr/local/bin/aescrypt -k {keyfile} [-s 128|192|256]

$ /storage/Users/currentUser/usr/local/bin/aesget
Usage: /storage/Users/currentUser/usr/local/bin/aesget -k {keyfile}

$ file /storage/Users/currentUser/usr/local/bin/aescrypt
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
```

- make check: 无测试套件（Makefile 中没有 check 目标）

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| aescrypt-0.7-ohos-aarch64.tar.gz | 159KB | 预编译包（含 bin/aescrypt、bin/aesget） |
| aescrypt-0.7-ohos-aarch64-debug.tar.gz | 59KB | 调试符号包 |

## 注意事项

- aescrypt 是一个加密/解密命令行工具，仅支持密钥文件模式（无 --version 标志）
- 该软件非常老旧（2001年），代码有多处指针类型不匹配警告（char* vs unsigned char*），但不影响功能
- Makefile install 目标不支持 DESTDIR，需要手动创建 staging 目录
---

**编译结束**: 2026-06-13 11:53
**最终状态**: built
