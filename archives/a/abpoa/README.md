# abpoa — adaptive Banded Partial Order Alignment

## 软件简介

abPOA 是一种自适应带状部分顺序比对（Partial Order Alignment）工具，用于快速构建多序列共识序列和多重序列比对（MSA）。它使用 SIMD 指令（通过 SIMDE 库实现跨平台可移植性）进行加速，支持全局、局部和扩展三种比对模式。

- **上游**: https://github.com/yangao07/abPOA
- **许可**: MIT
- **语言**: C
- **构建系统**: Makefile（非 autotools/cmake）

## 已编译版本

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 1.5.6 | published | 2026-06-18 | aarch64, clang 15.0.4, SIMDE header-only |

## 构建特点

- 纯 Makefile 构建，无 configure 脚本，无 install 目标
- 依赖 SIMDE（git 子模块，header-only）实现 SIMD 可移植性
- aarch64 平台自动选择 `-march=armv8-a+simd -D__AVX2__` SIMD 标志
- 产出静态库 libabpoa.a 和命令行工具 abpoa
- 运行时依赖: zlib, pthread, math（均为系统库）
