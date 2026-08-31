# fastk 1.2 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，无 configure）
- 编译日期: 2026-08-31
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

FastK 上游为纯 Makefile，CC 默认 gcc，需改为 clang。
make all 隐式构建三部分：
1. LIBDEFLATE 子库（make 进入 LIBDEFLATE/，生成 libdeflate.a）
2. HTSLIB 子库（make libhts.a，进入 HTSLIB/）
3. 15 个命令行工具

关键命令：
```bash
make CC=clang CFLAGS="... -fPIC -Drindex=strrchr" -j1
make install DEST_DIR=<package_folder>/bin
```

HTSLIB_static_LIBS（来自 HTSLIB/htslib_static.mk）= `-lz -lm -lbz2 -llzma -lcurl`，
链接依赖由 conan 依赖提供（zlib/bzip2/xz/libcurl）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `bzlib.h not found` | HTSLIB cram_io.c 需 bzip2 头文件，系统无 | conan 依赖 bzip2 提供 include 路径 |
| 2 | `undefined symbol: gzoffset` | 系统 libz.so(zlib 1.2.x) 无 gzoffset，需 conan zlib/1.3.1 | 用 conan zlib 静态库，-l:libz.a |
| 3 | `undefined symbol: rindex` | OHOS musl libc 未导出 rindex（BSD legacy） | CFLAGS 加 -Drindex=strrchr |
| 4 | LIBDEFLATE `ln: cannot create hard link gzip->gunzip` | 跨设备硬链接权限 | 不影响 libdeflate.a 生成，可忽略 |

## 源码修改

无补丁。rindex 问题通过 CFLAGS -Drindex=strrchr 解决（编译时宏替换，不修改源码）。

## 依赖版本

- zlib/1.3.1.1（系统同名库，静态，R26）
- bzip2/1.0.8（静态）
- xz/5.8.3（静态）
- libcurl/8.5.0（FastK 内部 HTSLIB 依赖，用于 hfile_libcurl）
- 内部捆绑：LIBDEFLATE、HTSLIB（make 时自动构建）

## 验证结果

```bash
$ ./FastK 2>&1 | head -3
Usage: FastK [-k<int(40)>] [-t[<int(1)>]] [-p[:<table>[.ktab]]] [-c] [-bc<int>]
             [-v] [-N<path_name>] [-P<dir($TMPDIR)>] [-M<int(12)>] [-T<int(4)>]
                 <source>[.cram|.[bs]am|.db|.dam|.f[ast][aq][.gz] ...
```
15 个工具全部编译成功。
---

**编译结束**: 2026-08-31 09:42
**最终状态**: built
