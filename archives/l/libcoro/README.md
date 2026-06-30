# libcoro — C coroutine library

## Overview
libcoro is a lightweight C coroutine library by Marc Lehmann, providing coroutine context switching functionality. It is the underlying C library used by the Perl Coro module.

## Source
The source code (coro.c and coro.h) is distributed as part of the Perl Coro module on CPAN. Version 6.513 is available from the CPAN BackPan historical archive.

- URL: https://backpan.cpan.org/modules/by-authors/id/M/ML/MLEHMANN/Coro-6.513.tar.gz

## Build Backend
On OHOS/aarch64, libcoro must be compiled with the CORO_SJLJ backend (-DCORO_SJLJ), as:
- CORO_UCONTEXT: musl/OHOS lacks ucontext functions
- CORO_PTHREAD: musl/OHOS lacks pthread_cancel
- CORO_ASM: aarch64 assembly is experimental/unstable

## Known Issues
- pthread_cancel is not available on musl/OHOS — patched with #ifdef __OHOS__ guard
- Source distribution is a Perl module (Coro), not a standalone C library — requires custom Makefile for standalone compilation

## Platform Adaptation (OHOS/aarch64)
- **Backend**: CORO_SJLJ (sigsetjmp/siglongjmp + sigaltstack)
- **UCONTEXT**: 不可用（musl/OHOS 缺少 getcontext/makecontext/swapcontext）
- **PTHREAD**: 不可用（musl/OHOS 缺少 pthread_cancel）
- **ASM**: 不稳定（aarch64 汇编标注 experimental）

## Functional Test Results
- **16项综合测试全部通过** (2026-06-01)
- 测试覆盖: 基本切换、参数传递、多协程交替、栈管理、嵌套链、状态保持、生产者-消费者、深递归、信号兼容、高频切换等
- 详见: reports/test-report.md

## Quality Status
- 所有已知问题已修复 ✅
- pkg-config 路径参数 (`-L${libdir}` / `-I${includedir}`) 修复完毕 ✅
- 预编译包已重新打包（包含正确的 strip + ELF 签名） ✅
- 上库评估: **✅ 可以上库**

## Compiled Versions
- 6.513: published (2026-06-01)
