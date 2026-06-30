# sparse — C 语义解析与静态分析工具

Sparse 是一个 C 语言的语义解析器，主要用于 C 代码的静态分析。它能够检测常见的编码错误，如：
- 赋值表达式用作条件判断
- 未声明为 static 的内部符号
- 类型不匹配
- 内存操作问题

Sparse 由 Linux 内核开发者 Linus Torvalds 创建，广泛用于 Linux 内核代码的静态检查。

## 功能特性

- **静态分析**: 检测 C 代码中的潜在缺陷和编码风格问题
- **语义解析**: 提供 C 语言前端供其他编译工具使用
- **多目标支持**: 支持 alpha, arm, arm64, mips, ppc, riscv, x86 等多种架构目标
- **cgcc 前端**: 作为 gcc 的替代前端，在编译时同时进行静态检查（需要 Perl）

## OpenHarmony 平台适配说明

- 构建系统: 纯 Makefile（无 configure 脚本）
- 编译命令: `make CC=clang-wrapper PREFIX=$DEFAULT_PREFIX`
- cgcc 需要 Perl 运行环境，OpenHarmony 未预装 Perl

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|----------|------|
| 0.6.4 | built | 2026-06-03 | 核心静态分析功能正常，cgcc 因缺 Perl 不可用 |