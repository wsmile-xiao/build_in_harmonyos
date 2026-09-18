# libmoe

> 处理多字节字符编码的 C 库（含调试工具 `mbconv`）。

## 简介

libmoe 以 CES（character encoding scheme）抽象处理多字节字符编码：ISO-2022-JP、EUC-JP、
Shift_JIS、UTF-8 等，提供字符集识别、按宽度换行/截断、编码转换与错误控制。随库附带的
`mbconv` 是一个命令行前端，用于按命令行参数转换文件或标准输入的编码（上游定位为
"mainly written for debugging of the library"）。

## OHOS 适配要点

- 上游是裸 `Makefile`，`CC=gcc`、`CPP=gcc -E`、`LD=gcc`、`AR=ar`，并安装到 `/usr/local`：
  本仓库用 Conan 提供的 clang 编译（`llvm-ar`/`llvm-ranlib`），并把
  `INCDIR/LIBADIR/LIBSODIR/BINDIR/LIBEXECDIR/MANDIR` 全部改写到包目录。
- **必须加 `-fgnu89-inline`**：2000 年代 C 代码使用 GNU89 的 `extern inline` 语义，
  现代 clang（默认 gnu17）会报 `redefinition of a extern inline function is not supported
  in C99 mode`。
- 传 make 参数时 `CF`（多词）与带参数的 `CPP`（`<clang> -E`）必须加引号，否则 make 会把
  它们拆成多个目标（`No rule to make target 'pic'`）。
- 头文件由 `*.mk_btri.h` 经 C 预处理器喂给上游自举工具 `mk_btri` 生成，因此也要传 `CPP`。
- CLI 工具 → 提供软件级 `commands.json`（R38/L0k）。
- 上游 `test.pl` 只打印 CES 边界常量（无断言）→ R51 上游步骤申报 `not_applicable`，
  验证由 `test_package` 的 harness 承担。
- 产物：`lib/libmoe.so.1.5.8`、`lib/libmoe.a`、`include/moe/*.h`、`bin/mbconv`、
  `share/man/man1/mbconv.1.gz`。

## 依赖

无（仅 libc）。

## 使用

```sh
# 库：链接 -lmoe，头文件在 include/moe/
cc -I<prefix>/include/moe app.c -L<prefix>/lib -lmoe

# 工具：把文件从默认 CES 转为 UTF-8 输出
mbconv -c UTF-8 input.txt
# 从标准输入转换并写到文件
printf 'ASCII only\n' | mbconv -t out.txt -
```

## 功能验证

```sh
conan create archives/l/libmoe/1.5.8 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# rc=0；harness 10/10（安装布局 + mbconv 确定性转换）
```
