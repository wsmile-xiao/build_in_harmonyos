# spim — MIPS32 模拟器

## 简介

spim 是一个 MIPS R2000/R3000 汇编语言模拟器，由 James R. Larus 开发。它可运行 MIPS 汇编程序，支持交互式和批处理模式，广泛用于计算机体系结构课程教学。

## 版本信息

| 版本 | 状态 | 日期 |
|------|------|------|
| 9.1.24 | published | 2026-06-08 |

## 特性

- MIPS32 指令集模拟（含延迟分支/延迟加载模式）
- 交互式命令行界面（可单步执行、查看寄存器/内存）
- 支持裸机模式（-bare）和扩展模式（-asm）
- 内置异常处理器（exceptions.s）
- 支持内存映射 IO（-mapped_io）
- 支持浮点运算（FPU）

## 编译说明

- **构建系统**: 纯 Makefile（非 autotools）
- **链接器**: 必须使用 GNU ld (ld.bfd) 替代 lld（`-fuse-ld=/data/service/hnp/bin/ld.bfd`）
- **源码结构**: tarball 包含 CPU/spim/Tests/Documentation 嵌套目录，需完整解压后在 spim 子目录编译
- **依赖**: flex 2.6.4, bison 3.8.2（编译时需要）

## 运行时依赖

- libc (ld-musl-aarch64.so.1)
- libm
- 无额外三方库依赖

## 许可证

BSD License