# tinycdb 0.81 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，非 autotools）
- 编译日期: 2026-06-09
- 编译器: clang 15.0.4 / GNU ld (ld.bfd)
- 状态: published
- 无外部依赖（纯 C 库，仅 libc）

## 编译步骤

tinycdb 是纯 Makefile 构建，无 configure 脚本。使用 make 命令行参数覆盖编译器设置：

```bash
# 编译
make CC=clang AR=llvm-ar RANLIB=llvm-ranlib \
  LDFLAGS="-fuse-ld=/data/service/hnp/bin/ld.bfd" \
  CFLAGS="-fPIC -O2" \
  prefix=$DEFAULT_PREFIX \
  -j1
```

编译输出（真实执行）：
```
clang -fPIC -O2 -D_FILE_OFFSET_BITS=64 -c cdb_init.c
clang -fPIC -O2 -D_FILE_OFFSET_BITS=64 -c cdb_find.c
clang -fPIC -O2 -D_FILE_OFFSET_BITS=64 -c cdb_findnext.c
clang -fPIC -O2 -D_FILE_OFFSET_BITS=64 -c cdb_seq.c
clang -fPIC -O2 -D_FILE_OFFSET_BITS=64 -c cdb_seek.c
clang -fPIC -O2 -D_FILE_OFFSET_BITS=64 -c cdb_pack.c
clang -fPIC -O2 -D_FILE_OFFSET_BITS=64 -c cdb_unpack.c
clang -fPIC -O2 -D_FILE_OFFSET_BITS=64 -c cdb_make_add.c
clang -fPIC -O2 -D_FILE_OFFSET_BITS=64 -c cdb_make_put.c
clang -fPIC -O2 -D_FILE_OFFSET_BITS=64 -c cdb_make.c
clang -fPIC -O2 -D_FILE_OFFSET_BITS=64 -c cdb_hash.c
rm -f libcdb.a
llvm-ar rv libcdb.a cdb_init.o cdb_find.o cdb_findnext.o cdb_seq.o cdb_seek.o cdb_pack.o cdb_unpack.o cdb_make_add.o cdb_make_put.o cdb_make.o cdb_hash.o
llvm-ranlib libcdb.a
clang -fPIC -O2 -D_FILE_OFFSET_BITS=64 -c cdb.c
clang -fuse-ld=/data/service/hnp/bin/ld.bfd -o cdb cdb.o libcdb.a
```

安装 staging（带 DESTDIR）：
```bash
make CC=clang AR=llvm-ar RANLIB=llvm-ranlib \
  LDFLAGS="-fuse-ld=/data/service/hnp/bin/ld.bfd" \
  CFLAGS="-fPIC -O2" \
  prefix=$DEFAULT_PREFIX \
  DESTDIR=$TEST_PREFIX \
  install
```

安装到 $DEFAULT_PREFIX（不带 DESTDIR）：
```bash
make CC=clang AR=llvm-ar RANLIB=llvm-ranlib \
  LDFLAGS="-fuse-ld=/data/service/hnp/bin/ld.bfd" \
  CFLAGS="-fPIC -O2" \
  prefix=$DEFAULT_PREFIX \
  install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | make check 测试失败：`./cdb: Permission denied` | 新编译的二进制未 ELF 签名，鸿蒙系统禁止执行未签名二进制 | `python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf cdb` 签名后可正常执行 |
| 2 | make check 中 ulimit -f 文件大小限制测试差异 | OpenHarmony 不支持 `ulimit -f` 文件大小限制（musl libc 不实现该资源限制） | 平台限制，不影响软件功能，记录为已知差异 |
| 3 | 需使用 GNU ld 替代 lld | lld 不兼容部分链接行为 | `LDFLAGS="-fuse-ld=/data/service/hnp/bin/ld.bfd"` |

## 源码修改

无源码修改，仅通过 make 命令行参数适配。Makefile 原生支持 DESTDIR，无需修改。

## 依赖版本

无外部依赖（纯 C 库，仅 libc）

## 验证结果

### 命令行工具验证

```bash
$ $DEFAULT_PREFIX/bin/cdb -h
cdb: Constant DataBase (CDB) tool version 0.80. Usage is:
 query:  cdb -q [-m] [-n recno|-a] cdbfile key
 dump:   cdb -d [-m] [cdbfile|-]
 list:   cdb -l [-m] [cdbfile|-]
 create:  cdb -c [-m] [-wrue0] [-t tempfile|-] [-p perms] cdbfile [infile...]
 stats:  cdb -s [cdbfile|-]
 help:   cdb -h
```

### 创建数据库

```bash
$ echo "+3,4:one->here
+1,1:a->b
+1,3:b->abc
+3,4:one->also
" | $DEFAULT_PREFIX/bin/cdb -c $TMPDIR/func-test.cdb
退出码: 0
```

### 查询

```bash
$ $DEFAULT_PREFIX/bin/cdb -q $TMPDIR/func-test.cdb one
herealso
退出码: 0
```

### 查询不存在键

```bash
$ $DEFAULT_PREFIX/bin/cdb -q $TMPDIR/func-test.cdb nonexistent
退出码: 100  （符合预期，100 表示未找到）
```

### 导出

```bash
$ $DEFAULT_PREFIX/bin/cdb -d $TMPDIR/func-test.cdb
+3,4:one->here
+1,1:a->b
+1,3:b->abc
+3,4:one->also
退出码: 0
```

### 统计

```bash
$ $DEFAULT_PREFIX/bin/cdb -s $TMPDIR/func-test.cdb
number of records: 4
key min/avg/max length: 1/2/3
val min/avg/max length: 1/3/4
hash tables/entries/collisions: 3/8/1
hash table min/avg/max length: 2/3/4
hash table distances:
 d0:      3 75%
 d1:      1 25%
 d2~d9:   0  0%
退出码: 0
```

### 列表

```bash
$ $DEFAULT_PREFIX/bin/cdb -l $TMPDIR/func-test.cdb
+3:one
+1:a
+1:b
+3:one
退出码: 0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| tinycdb-0.81-ohos-aarch64.tar.gz | 152KB | 预编译包（ELF 已签名、已 strip） |
| tinycdb-0.81-ohos-aarch64-debug.tar.gz | 32KB | 调试符号包 |

## 安装产物清单

| 产物 | 路径 | 大小 |
|------|------|------|
| cdb 命令行工具 | `$DEFAULT_PREFIX/bin/cdb` | 43328 字节 |
| cdb.h 头文件 | `$DEFAULT_PREFIX/include/cdb.h` | 5126 字节 |
| libcdb.a 静态库 | `$DEFAULT_PREFIX/lib/libcdb.a` | 22764 字节 |
| libcdb.pc pkg-config | `$DEFAULT_PREFIX/lib/pkgconfig/libcdb.pc` | 229 字节 |
| cdb.1 man 手册 | `$DEFAULT_PREFIX/man/man1/cdb.1` | 6847 字节 |
| cdb.3 man 手册 | `$DEFAULT_PREFIX/man/man3/cdb.3` | 20363 字节 |
| cdb.5 man 手册 | `$DEFAULT_PREFIX/man/man5/cdb.5` | 3045 字节 |

## 注意事项

- ⭐ 必须使用 GNU ld（`-fuse-ld=/data/service/hnp/bin/ld.bfd`），不能使用 lld
- Makefile 默认目标是 `static`（libcdb.a + cdb），不构建共享库
- 测试中的 `ulimit -f` 在 OpenHarmony 上不生效（平台限制），不影响软件功能
- 新编译的二进制需要 ELF 签名（`sign-elf`）才能在鸿蒙系统上执行---

**编译结束**: 2026-06-09 16:09
**最终状态**: published
---

**编译结束**: 2026-07-15 17:57
**最终状态**: built
