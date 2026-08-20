# SPIRV-LLVM-Translator

LLVM-based translator for SPIR-V (LLVM IR <-> SPIR-V)。

## 版本

- 20.1.0 — 基于 LLVM 20.1.0

## 构建产物

- `lib/libLLVMSPIRVLib.a` — SPIR-V 翻译静态库
- `bin/llvm-spirv` — 命令行翻译工具
- `include/LLVMSPIRVLib/` — 头文件

## 依赖

- `llvm/20.1.0` (已发布到 ohpcd 制品仓)

## 上游

- 仓库: https://github.com/KhronosGroup/SPIRV-LLVM-Translator
- License: Apache-2.0 WITH LLVM-exception
