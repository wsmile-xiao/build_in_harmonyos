# UASM

> MASM 兼容的 x86 汇编器（UASM，Open Watcom Public License）。可生成
> `bin` / `coff` / `elf64` / `win64` / `macho64` / `mz` 等目标格式。

## 简介

UASM 是 HJWasm/UASM 谱系的 MASM 兼容汇编器，纯 C 实现，无三方依赖。
支持大量 x86/x64 指令（含 AVX/AVX-512/EVEX）、宏、结构体、条件汇编与
多种目标文件格式，是构建 Windows/ELF/Mach-O 对象的通用工具。

## OHOS 适配要点

- 用上游 `Makefile-Linux-GCC-64.mak` + OHOS clang 构建；`CFLAGS` 需
  `-O0`，并降级 clang≥16 的若干提升为错误的警告。
- `codegenv2.c` 在 aarch64 `-O2` 下被误编译（VEX/EVEX 编码错误），
  必须 `-O0`。
- `expreval.c` 的 32 位 `SHR` 语义依赖 `unsigned long` 的位宽，
  LP64 下需改为 `uint_32`。
- 上游回归套件为 Windows 专用，本包移植为 POSIX 运行器并纳入构建验证。

详见 [`2.57/notes.md`](2.57/notes.md)。

## 依赖

| 依赖 | 版本 | 说明 |
| --- | --- | --- |
| 无 | - | 仅 C 标准库 |

## 用法

```sh
uasm -q -bin prog.asm          # 平铺二进制
uasm -q -elf64 prog.asm        # ELF64 可重定位目标（prog.o）
uasm -q -win64 prog.asm        # Win64 COFF 目标
uasm                           # 打印版本与用法
```

## 参考

- [源码仓库](https://github.com/Terraspace/UASM)
