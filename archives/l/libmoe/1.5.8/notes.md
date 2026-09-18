# libmoe 1.5.8 适配笔记

## 编译环境
- 构建系统: 上游裸 `Makefile`（无 configure）
- 编译日期: 2026-09-18
- 编译器: OHOS clang（Conan profile `ohos-aarch64`）
- 辅助工具: `perl` + `pod2man`（生成 man 页）、`mk_btri`（上游自举工具，用于由 `*.mk_btri.h` 生成头文件）
- 状态: built

## 版本与源码
- 平台版本 `1.5.8` == Debian `libmoe_1.5.8.orig.tar.gz`
- sha256 `474f962687551849b2a677be29471927321e5a3b62c3bbf87d3afd0fdf27e0e3`
- 上游无独立 COPYING；许可声明在 `libmoe.shtml` 内，随包安装到 `licenses/`（Debian 归类为 BSD-3-Clause）

## 产物
- `lib/libmoe.so.1.5.8`（+ `.so.1.5`、`.so` 软链）、`lib/libmoe.a`
- `include/moe/`：12 个公共头（`mb.h`、`mbces.h`、`mbcesdefs.h`、`mbcesconf.h`、`mblangconf.h`、
  `mbversion.h`、`altmalloc.h`、`btri.h`、`uirx.h`、`wcrx.h` 等）
- `bin/mbconv`、`libexec/moe/mk_btri`
- `share/man/man1/mbconv.1.gz`
- `licenses/libmoe.shtml`
- 软件级 `commands.json`（CLI 工具，R38/L0k）

## 构建要点（上游 Makefile 的全量变量覆盖）

```sh
make -j1 \
  CC=<clang> CPP='<clang> -E' LD=<clang> \
  AR=llvm-ar RANLIB=llvm-ranlib \
  CF='-O2 -Wall -fpic -fgnu89-inline -I.' all libmoe.so
make ... install PREFIX=<pkg> \
  INCDIR=<pkg>/include/moe LIBADIR=<pkg>/lib LIBSODIR=<pkg>/lib \
  BINDIR=<pkg>/bin LIBEXECDIR=<pkg>/libexec/moe MANDIR=<pkg>/share/man
```

| # | 问题 | 原因 | 处理 |
|---|------|------|------|
| 1 | `make: pic: No such file or directory` / `No rule to make target 'pic'` | `CF=-O2 -Wall -fpic -I.` 未加引号，被 make 拆成多个目标 | 传参时用 `shlex.quote`（`CF='...'`；`CPP` 因为带 `-E` 同样要引号） |
| 2 | `error: redefinition of a 'extern inline' function ... not supported in C99 mode` | 2000 年代 C 工程使用 GNU89 `extern inline` 语义；clang 默认 gnu17 | 加 `-fgnu89-inline`（比 `-std=gnu89` 改动更小） |
| 3 | 上游 `install` 写死 `/usr/local` | Makefile 的 `DESTDIR/PREFIX/INCDIR/LIBADIR/...` | 全部以 make 变量改写到包目录（含 `MANDIR=share/man`） |
| 4 | 头文件生成依赖 C 预处理器与自举工具 | `${BTRI_Hs}: %.h: %.mk_btri.h mk_btri` 规则把 `*.mk_btri.h` 经 `$(CPP)` 喂给 `mk_btri` | 显式传 `CPP='<clang> -E'`，`make all` 会先构建 `mk_btri` |
| 5 | 版本 `1.5.8` 与上游 `version.mak` 一致 | — | 归档目录直接用 `1.5.8` |

## 上游行为要点（消费者测试依据）

- `mbconv` 从文件或 **stdin** 读取，按 `-c <converters>` / `-cs <charset>` 指定的 CES 转换后写 stdout
  或 `-t <file>`。
- ASCII 载荷在默认、`:UTF-8` 与 `-c ASCII` 三种情形下都与原文逐字节一致（实测）。
- `-h`/`--help` 打印用法摘要（含 `mbconv` 与 `libmoe` 版本串）。
- 上游 `test.pl` 只是打印 CES 边界常量（无断言、未接入 Makefile）→ R51 上游步骤申报
  `not_applicable`。

## 消费者测试（10 项检查）

`test_package/test_libmoe.py`：

1. `bin/mbconv` 存在
2. `lib/libmoe.a` 已安装
3. `include/moe/mb.h` 已安装
4. man 页已安装
5. ASCII 输入原样透传
6. `-cs UTF-8` 下 ASCII 载荷不变
7. `-c ASCII` 转换成功且载荷不变
8. `-t <file>` 写出的内容与 stdout 相同
9. 显式 `-` 输入可用
10. `-h` 打印用法摘要

## 验证结果

```sh
conan create archives/l/libmoe/1.5.8 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# rc=0；harness 10/10
```
