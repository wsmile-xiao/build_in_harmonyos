# fpart 1.7.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-17
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. init-build: `python3 ohc-run.py init-build fpart 1.7.0 --url=https://github.com/martymac/fpart/archive/refs/tags/fpart-1.7.0.tar.gz`
2. GitHub 源码包缺少 configure/Makefile.in，需先 `autoreconf -fi` 生成构建文件
3. configure: `bash ./configure --prefix=$DEFAULT_PREFIX --enable-embfts`（注意: E011 修复需先 sed umask 077→022）
4. make: `make -j1`
5. make install DESTDIR: `make install DESTDIR=$TEST_PREFIX`
6. verify-build: `python3 ohc-run.py verify-build fpart 1.7.0 --install-prefix=$TEST_PREFIX/$DEFAULT_PREFIX`
7. package: `python3 ohc-run.py package fpart 1.7.0`
8. make install: `make install`（模拟用户部署到 $DEFAULT_PREFIX）
9. 用户验证: `fpart --version` → fpart v1.7.0 (fts=embedded)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status: can't create ./confXXX/subs1.awk: Permission denied | E011: HMDFS UID 映射导致 umask 077 创建的目录不可写 | `sed -i 's/umask 077/umask 022/g' configure` |
| 2 | 'fts.h' file not found with <angled> include | E105: musl libc 不提供 fts.h，且 OHOS host_os 不被识别为 linux-musl | `./configure --enable-embfts` 手动启用嵌入式 fts |
| 3 | GitHub tarball 缺少 configure 和 Makefile.in | 非 release tarball，autotools 生成文件未包含 | `autoreconf -fi` 生成 |

## 源码修改

1. configure: umask 077 → umask 022 (E011 修复)
   - track-edit 已记录

## 依赖版本

- clang 15.0.4
- autoconf 2.72
- automake 1.17
- gawk (预编译包)
- GNU coreutils ginstall/mkdir (预编译包)
- musl libc (系统)

## 验证结果

### 版本确认
```bash
$ fpart --version
fpart v1.7.0
Copyright (c) 2011-2025 Ganael LAPLANCHE <ganael.laplanche@martymac.org>
WWW: http://contribs.martymac.org
Build options: debug=no, fts=embedded
Long options are supported
```

### 功能测试 — 按分区数
```bash
$ mkdir -p /tmp/fpart-test/sub1 /tmp/fpart-test/sub2
$ echo "hello" > /tmp/fpart-test/sub1/a.txt
$ echo "world" > /tmp/fpart-test/sub1/b.txt
$ echo "test" > /tmp/fpart-test/sub2/c.txt
$ echo "data" > /tmp/fpart-test/sub2/d.txt
$ echo "more" > /tmp/fpart-test/e.txt

$ fpart -n 2 /tmp/fpart-test
Part #1: size = 16, files = 3
Part #2: size = 11, files = 2
1       6       /tmp/fpart-test/sub1/a.txt
2       6       /tmp/fpart-test/sub1/b.txt
1       5       /tmp/fpart-test/sub2/c.txt
2       5       /tmp/fpart-test/sub2/d.txt
1       5       /tmp/fpart-test/e.txt
```

### 功能测试 — 按大小限制
```bash
$ fpart -s 10 /tmp/fpart-test
Part #1: size = 6, files = 1
Part #2: size = 6, files = 1
Part #3: size = 10, files = 2
Part #4: size = 5, files = 1
```

### 功能测试 — verbose 模式
```bash
$ fpart -n 2 -v /tmp/fpart-test
Examining filesystem...
Sorting entries...
Part #1: size = 16, files = 3
Part #2: size = 11, files = 2
Summary: size = 27, files = 5, parts = 2
Writing output lists...
```

### 功能测试 — 输出到文件
```bash
$ fpart -n 2 -o /tmp/fpart-test/out /tmp/fpart-test
Part #1: size = 16, files = 3
Part #2: size = 11, files = 2
$ cat /tmp/fpart-test/out.1
/tmp/fpart-test/sub1/a.txt
/tmp/fpart-test/sub2/c.txt
/tmp/fpart-test/e.txt
$ cat /tmp/fpart-test/out.2
/tmp/fpart-test/sub1/b.txt
/tmp/fpart-test/sub2/d.txt
```

### fpsync 功能测试
```bash
$ fpsync --version
fpsync v1.7.0 - Sync directories in parallel using fpart

$ fpsync -l
<=== Listing runs
```

### ELF 二进制信息
```
ELF64, 2's complement, little endian, DYN (PIE), Machine: AArch64
依赖库: libc.so (musl libc)
BIND_NOW | PIE (无 RPATH 问题)
```

### fpsync 类型
```
fpsync: /bin/sh script (shell 脚本，无需 ELF 签名)
```

## make check

fpart 上游没有正式的自动化测试套件。`make check` 返回 "Nothing to be done for 'check'"。
源码 `tests/` 目录仅含 `fake_readdir.c` 和 `test-parent_path.c`，未集成到 Makefile。
通过上述手动功能测试充分验证编译产物可用性。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| fpart-1.7.0-ohos-aarch64.tar.gz | 182KB | 预编译包(ELF签名，含bin/fpart + bin/fpsync + man pages) |
| fpart-1.7.0-ohos-aarch64-debug.tar.gz | 31KB | debug symbols |

打包产物内容清单:
```
bin/
bin/fpart
bin/fpsync
lib/
lib/external/
share/
share/man/
share/man/man1/
share/man/man1/fpart.1
share/man/man1/fpsync.1
```

## 注意事项

- 必须使用 --enable-embfts 编译选项，否则 fts.h 编译失败
- 需先 autoreconf -fi 生成构建文件（GitHub 源码包不包含 autotools 生成文件）
- verify-build 需指定 --install-prefix=$TEST_PREFIX/$DEFAULT_PREFIX（DESTDIR 模式）
- 知识图谱草稿: E105 (OHOS host_os fts 检测遗漏)
---

**编译结束**: 2026-06-17 02:17
**最终状态**: published
