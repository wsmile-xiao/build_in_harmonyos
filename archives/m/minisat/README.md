# minisat

Minimalistic and high-performance SAT solver.

## 功能概述

- SAT (Boolean satisfiability) 问题求解器
- 支持核心求解器和简化求解器两种模式
- 支持 DIMACS CNF 格式输入（plain/gzipped）
- 高性能设计，适用于大规模约束满足问题

## OHOS 适配

- **fpu_control.h 缺失**: aarch64/OHOS 平台不支持 x86 FPU 控制头文件，需在 System.h 中使用 `#ifdef __OHOS__` 守卫排除
- **lld 链接器问题**: OHOS SDK 的 lld 链接器依赖 libxml2.so.16 但无法加载，需使用 `-fuse-ld=bfd` 替代
- **cmake 版本兼容性**: cmake 4.x 不兼容 `cmake_minimum_required(VERSION 2.6)`，需添加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`

## 依赖关系

- **编译依赖**: zlib (1.3.1+)
- **运行依赖**: zlib, libc (musl)

## 参考资料

- 官网: https://minisat.se/
- 源码: https://github.com/stp/minisat
- License: MIT