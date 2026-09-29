# lfortran

> LFortran —— LLVM 系现代 Fortran 编译器的 OpenHarmony/HarmonyOS PC 适配包。

## 是什么

LFortran 是一个基于 LLVM 的开源现代 Fortran 编译器（BSD-3-Clause），采用 ASR
（Abstract Semantic Representation）中间表示，支持 LLVM / C / C++ / x86 / WASM /
Julia 等多后端。本包交付完整编译器：`bin/lfortran` 前端 + `lib/` 运行时
（`liblfortran_runtime.{so,a}` 与 Fortran 运行时 `.mod` 模块）。

## 功能概述

- Fortran 2018 前沿特性 + 交互式 REPL
- LLVM 后端（本包 AArch64 原生）+ C/C++/Julia/Fortran 源码级后端
- `--show-asr` / `--show-llvm` / `--show-c` 中间表示检视、`--json` 序列化输出
- 自举式运行时模块（iso_fortran_env / iso_c_binding / ieee_arithmetic / omp_lib）

## OHOS 适配要点

1. **LLVM 依赖走 clang/22.1.8 包**：制品仓无独立 LLVM 包；clang/22.1.8 以
   `LLVM_BUILD_LLVM_DYLIB=ON` 聚合出 libLLVM.so（已签名）+ LLVMConfig.cmake
   （AArch64 target）。lfortran 对 dylib 模式的 LLVM 有原生回退分支
   （llvm/llvm-project#34593）。
2. **真机原生自举**：不设 CMAKE_SYSTEM_NAME，保持 native；以 Platform/HarmonyOS.cmake
   桩补 cmake 平台模块缺失；构建期以刚产出的 lfortran 二进制自举 Fortran 运行时模块。
3. **zlib/zstd 静态链接**：上游 finder 静态优先 + 系统同名库静态（R26），缩小签名面。
4. **OHOS XPM 签名**：包内 ELF 统一 binary-sign-tool 自签（clang 包同款口径）。

## 依赖关系

- 编译依赖：clang/22.1.8（LLVM）、zlib/1.3.2、zstd/1.5.7.1、rapidjson/1.1.0.1
- 运行依赖：libc / libm / libLLVM.so（clang 包提供）

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.64.0 | built | 首个适配版本（HarmonyOS PC aarch64，LLVM 后端） |

## 参考资料

- 上游官网：https://lfortran.org
- 上游仓库：https://github.com/lfortran/lfortran
- 运行时库独立包：archives/l/lfortran-runtime/（0.61.0，仅 C 运行时库）
