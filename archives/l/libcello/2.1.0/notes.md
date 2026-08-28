# libcello 2.1.0 适配笔记

## 编译环境
- 构建系统: makefile (上游手写 GNU make Makefile，无 CMake/autotools)
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos, OHOS 适配版)
- 目标: OHOS arm64 (musl libc sysroot)
- 状态: built (零补丁)

## 源码核实
- 上游仓库: https://github.com/orangeduck/Cello (官方，作者 Daniel Holden / orangeduck)
- 官方主页: https://libcello.org/
- 2.1.0 git tag: `2.1.0` (commit da28eefbc95d8bd5628e5f1c4cc12bc1b13fef4f)
- tarball URL: https://codeload.github.com/orangeduck/Cello/tar.gz/refs/tags/2.1.0
- SHA256: c138d974325fcb9640307c8b2d5dcc2d7127a1ccc5589d6c0794f86a5cb4001d
- License: BSD-2-Clause (LICENSE.md)

## 构建产物
- 静态库: libCello.a
- 动态库: libCello.so
- 头文件: include/Cello.h (单一头文件)
- 源文件: src/*.c (27 个)

## 构建参数 (与上游 Makefile Linux 分支一致)
- CC: clang (OHOS 适配版，profile 中 tools.build:compiler_executables)
- AR: llvm-ar
- CFLAGS: -I./include -std=gnu99 -Wall -Wno-unused -fPIC [-O2 -DNDEBUG for Release]
- LIBS: -lpthread -lm (OHOS musl 系统库，均为真实可用)
- LFLAGS: (空)

## 零补丁验证 (任务 #4/#5)
对 src/ + include/ + tests/ 进行了完整移植性审计：

### GCC 扩展检查
- 无 `__builtin_*`、`__attribute__`、`typeof`、statement-expression、`__asm__`、`__thread`
- 仅使用 `-std=gnu99`（Cello 用 `is` 宏重定义 `==`，属标准 C 预处理器特性，非 GCC 专有）
- OHOS clang 默认支持 gnu99，无需改 ISO C99

### glibc-only / Linux-specific API 检查
- `#include <pthread.h>` — OHOS musl 提供 ✅
- `#include <execinfo.h>` — OHOS musl 提供 ✅（libc.so 内含 backtrace/backtrace_symbols 真实 T 符号）
- `pthread_main_np()` — 仅在 `#ifdef CELLO_MAC` 分支调用，OHOS 不走该分支 ✅
- Exception.c 使用 `signal(SIGABRT/SIGFPE/SIGILL/SIGINT/SIGSEGV/SIGTERM, ...)` — 标准 C signal.h ✅
- Thread.c 使用 pthread_create/join/kill/mutex/key_create — POSIX，musl 全部提供 ✅
- 无 sysconf/prctl/syscall/clone/CPU_SET/setrlimit/getauxval 等 Linux-only 调用

### execinfo / backtrace 真实链接验证
```
OHOS musl libc.so 符号表:
  0000000000011d80 T backtrace
  0000000000011d80 T backtrace_symbols
  0000000000011d80 T backtrace_symbols_fd
```
backtrace 功能真实可用，**不强制 CELLO_NSTRACE 掩盖**（符合"不通过关闭关键功能掩盖问题"要求）。

### 端到端零补丁构建
```
make -j4 CC=clang AR=llvm-ar CFLAGS="-I./include -std=gnu99 -Wall -Wno-unused -fPIC" LIBS="-lpthread -lm"
→ libCello.a (462840 bytes, OHOS arm64)
→ libCello.so (346432 bytes, ELF shared object 64-bit LSB arm64)
```
27 个 .c 全部编译通过，仅 OHOS 链接器惯有 warning（--code-sign 等，非错误）。

## 上游测试 (任务 #6)
运行 `make check`（官方 tests/test.c，基于 ptest.h）：

| 项 | Total | Passed | Failed |
|----|-------|--------|--------|
| Suites | 21 | 21 | 0 |
| Tests | 133 | 133 | 0 |
| Asserts | 1639 | 1639 | 0 |

涵盖 Array/Assign/Cmp/Concat/Doc/Exception/File/Function/GC/Get/Hash/Iter/Len/List/Num/Pointer/Push/Resize/Show/Start/String/Table/Thread/Tree/Tuple/Type/Zip 等 21 个测试套件，全部通过。

## test_package (任务 #7)
消费者视角验证：真正 include <Cello.h> 并链接 libCello.a，构建并运行核心对象/容器/函数调用，验证实际值与生命周期（非仅编译）。见 test_package/test.c。

## 系统链接依赖 (任务 #8)
- libm: 是（src/Num.c 用 floor/fmod/frexp 等；test_package 验证）
- pthread: 是（src/Thread.c pthread_*, src/Exception.c signal 相关）
- execinfo: 否（backtrace 已在 musl libc.so 内，无需单独 -lexecinfo）
- 其他: 无

---

**编译结束**: 2026-08-27
**最终状态**: built (零补丁)
