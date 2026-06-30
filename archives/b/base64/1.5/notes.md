# base64 1.5 适配笔记

## 编译环境
- 构建系统: autotools (GNU Autoconf 2.59)
- 编译日期: 2026-05-28
- 编译器: clang 15.0.4 (llvm-release)
- 平台: OpenHarmony ARM64 (HMDFS)
- TMPDIR: /storage/Users/currentUser/tmp
- DEFAULT_PREFIX: /storage/Users/currentUser/usr/local
- 状态: published

## 编译步骤（真实执行）

### 1. 初始化
```
python3 $SKILL_ROOT/scripts/ohc-run.py init-build base64 1.5 --url=https://www.fourmilab.ch/webtools/base64/base64-1.5.tar.gz
```
注意：SSL证书问题导致脚本下载失败，需手动 `curl -kL` 下载后用 `--no-download` 重新初始化。

### 2. 补丁应用 — configure 脚本 mktemp 修复
**问题**: configure 生成的 config.status 使用 `mktemp -d -q "./confstatXXXXXX"` 在 HMDFS 上创建临时目录后无法写入文件，导致 Makefile 和 config.h 无法生成。

**根因**: HMDFS 对 mktemp 创建的目录有权限限制（R10: /tmp 只读），即使移到 $TMPDIR，mktemp 的 umask 077 仍导致子进程写入失败。

**解决方案**: 替换 mktemp 整块逻辑为 `mkdir -p ${TMPDIR}/confstat$$-$RANDOM`（不用 umask 077）：
```bash
# 原始代码 (configure 内嵌 config.status 模板):
tmp=`(umask 077 && mktemp -d -q "./confstatXXXXXX") 2>/dev/null`

# 修复后:
tmp=${TMPDIR:-/tmp}/confstat$$-$RANDOM
mkdir -p $tmp && test -d $tmp
```

### 3. 补丁应用 — Makefile.in /tmp→$$TMPDIR
**问题**: Makefile.in 的 check/wringer 目标使用硬编码 `/tmp/`（35处），HMDFS 上 /tmp 是只读的（R10）。

**解决方案**: 全部替换 `/tmp/` → `$$TMPDIR/`。同时修复 install-bin/install-man 目标缺少 `mkdir -p` 规则的问题。

### 4. 配置与编译（真实执行）
```bash
cd $BUILD_SRC_DIR
./configure --prefix=$DEFAULT_PREFIX
# 输出:
# checking for gcc... clang
# checking for C compiler default output file name... a.out
# ...
# configure: creating ./config.status
# config.status: creating Makefile
# config.status: creating config.h

make -j2
# 输出:
# clang -fPIC -O2 -I/storage/Users/currentUser/usr/local/include -c -o base64.o base64.c
# clang -fPIC -O2 -I/storage/Users/currentUser/usr/local/include -c -o getopt.o getopt.c
# clang base64.o getopt.o -o base64 -fPIC -O2 -L/storage/Users/currentUser/usr/local/lib
```

### 5. Staging 安装
```bash
mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/bin
mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/man/man1
make install DESTDIR=$TEST_PREFIX
# 输出:
# ginstall -c base64 $TEST_PREFIX/$DEFAULT_PREFIX/bin/base64
# ginstall -c -m 644 base64.1 $TEST_PREFIX/$DEFAULT_PREFIX/man/man1/base64.1
```

Staging 产物验证：
```
$TEST_PREFIX/$DEFAULT_PREFIX/bin/base64     (27008 bytes, ELF64 ARM64)
$TEST_PREFIX/$DEFAULT_PREFIX/man/man1/base64.1  (3404 bytes)
```

### 6. 测试执行（真实输出）

**make check**:
```
All tests passed.
```

**make wringer (13层嵌套编码/解码)**:
```
Wringer test passed.
```

### 7. 预编译包制作
```
python3 $SKILL_ROOT/scripts/ohc-run.py package base64 1.5
```
产物:
- base64-1.5-ohos-aarch64.tar.gz (88KB): 含 bin/base64, man/man1/base64.1
- base64-1.5-ohos-aarch64-debug.tar.gz (31KB): 含 base64.debug 调试符号

### 8. 本地安装与验证
```bash
make install  # 不带 DESTDIR，安装到 ~/usr/local
/storage/Users/currentUser/usr/local/bin/base64 --version
# 输出:
# base64 1.5
# Last revised: 10th June 2007

echo "Hello OpenHarmony" | base64 --encode | base64 --decode
# 输出:
# Hello OpenHarmony
```

### 9. 收尾
```
python3 $SKILL_ROOT/scripts/ohc-run.py finish base64 1.5 published
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 铁律 |
|---|------|------|----------|------|
| 1 | init-build 下载失败 | SSL证书验证失败 | 手动 curl -kL 下载后 --no-download | — |
| 2 | config.status 无法创建 Makefile/config.h | HMDFS 上 mktemp 创建的目录权限问题 | 修改 configure 内嵌模板: mktemp→mkdir -p $TMPDIR | R10, R23 |
| 3 | make check 失败 "Read-only file system" | Makefile.in 硬编码 /tmp (HMDFS只读) | Makefile.in /tmp→$$TMPDIR (35处) | R10 |
| 4 | make install DESTDIR 失败 | install-bin 依赖 $(BINDIR) 目录前置条件，无 mkdir 规则 | Makefile.in 增加 mkdir -p 规则 | R20 |

## 源码修改清单

- **Makefile.in** (Patch 0001):
  - 替换 check/wringer 中 `/tmp/` → `$$TMPDIR/` (35处)
  - install-bin 增加 `mkdir -p $(BINDIR)` 规则
  - install-man 增加 `mkdir -p $(MAN1DIR)` 规则
  - 移除 install-bin 对 `$(BINDIR)` 的前置依赖
- **configure** (Patch 0002):
  - 内嵌 config.status 模板的 mktemp 临时目录逻辑 → mkdir -p $TMPDIR
  - 错误消息更新为显示 $TMPDIR 路径

注意：遵守 R6，只修改源文件（Makefile.in、configure），不修改生成文件（Makefile、config.status）。

## 依赖版本

无外部依赖（纯 C 实现，仅依赖 musl libc）

## 验证结果（真实执行）

```bash
$ /storage/Users/currentUser/usr/local/bin/base64 --version
base64 1.5
Last revised: 10th June 2007

$ echo "Hello OpenHarmony" | base64 --encode
SGVsbG8gT3Blbkhhcm1vbnkK

$ echo "Hello OpenHarmony" | base64 --encode | base64 --decode
Hello OpenHarmony

$ echo "Test123" > $TMPDIR/test_input.txt
$ base64 -e $TMPDIR/test_input.txt $TMPDIR/test_encoded.txt
$ cat $TMPDIR/test_encoded.txt
VGVzdDEyMwo=
$ base64 -d $TMPDIR/test_encoded.txt $TMPDIR/test_decoded.txt
$ cat $TMPDIR/test_decoded.txt
Test123

$ base64 --copyright
This program is in the public domain.
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| base64-1.5-ohos-aarch64.tar.gz | 88KB | 预编译包（含 debuglink, ELF签名） |
| base64-1.5-ohos-aarch64-debug.tar.gz | 31KB | 调试符号包 |
| 0001-Makefile.in.patch | 5.3KB | /tmp→$$TMPDIR 替换 + mkdir 规则 |
| 0002-configure.patch | 1.1KB | mktemp→mkdir+$TMPDIR 临时目录修复 |

## 二进制属性

```
$ file base64
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
$ readelf -h base64 | grep Machine
Machine: AArch64
```

## 注意事项

1. HMDFS 上 /tmp 是只读的，所有临时文件必须使用 $TMPDIR（R10）
2. Makefile 是生成文件，不可直接修改（R6）；只改 Makefile.in 源文件后重新 configure
3. mktemp 在 HMDFS 上创建的目录有权限问题，需用 mkdir -p 代替（R23 平台检测优先）
4. --version 输出多行文本，版本号在第一行可通过 `head -1` 提取
---

**编译结束**: 2026-06-01
**最终状态**: published
