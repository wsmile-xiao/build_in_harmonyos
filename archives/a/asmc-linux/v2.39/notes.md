# asmc-linux v2.39 适配笔记（HarmonyOS PC · ARM64 原生移植 · GNU make · CLI 工具）

## 定位
- 上游：nidud/asmc — 自举 x86 宏汇编器
- 本交付：**ARM64 原生移植**（aarch64_port/），非上游 x86 自举
- 构建系统：GNU make（Makefile，target aarch64-unknown-linux-ohos，clang 15.0.4）
- 交付形态：CLI 工具（package_type=application），bin/asmc_native

## 交付源码（aarch64_port/，随 conanfile.py exports_sources 打包）
- C：asmc_asm.c（解析/宏/类型/布局/目标编码）、asmc_elf.c（ELF 写出）、asmc_io.c、asmc_globals.c
- ASM：asmc_entry.s、asmc_runtime.s（AArch64 汇编端口）
- 头文件：asmc_data.h；构建：Makefile

## 已验证能力（ARM64 OHOS 原生）
1. ARM64 OHOS 原生运行 Asmc host（asmc_native 静态 ELF，Version 2.39.00）
2. Asmc 输出 x86/x86-64 目标（.o ELF64 x86-64 与 .bin 原始 x86 指令）
3. x86-64 可执行 ELF 可由本地 ld.lld 15.0.4 生成（-m elf_x86_64 -static -e main）
   - 修复：proc 符号输出为 STB_GLOBAL；.symtab 按 ELF 规范 LOCAL 在前/GLOBAL 在后、sh_info 正确

## 验证结果
- 固定 635-source manifest：PASS=635 FAIL=0
- 独立上游测试子集（105 用例）：PASS=105 FAIL=0
- 鸿蒙特有 smoke test：原生运行 + x86-64 目标产物 + ld.lld 链接 x86-64 可执行 ELF

## 架构说明
- 上游 asmc 为 x86-only 自举（bin/asmc64 无法在 aarch64 执行）；本移植用 AArch64 汇编 + C 重建
  host，保持 x86/x86-64 目标代码生成能力。不使用 QEMU/Wine/仿真/x86 host/固定输出/stub。

## 交付边界
- 交付：真实可维护源码（8 文件）、conanfile.py、conandata.yml、test_package、manifest、notes
- 排除：生成产物/对象/二进制/临时输入/全量构建产物/原始日志（build/、*.o、*.bin、asmc_native、
  r2*_evidence/、r2*_progress*.txt 等）
---

**编译结束**: 2026-08-28 19:33
**最终状态**: built
