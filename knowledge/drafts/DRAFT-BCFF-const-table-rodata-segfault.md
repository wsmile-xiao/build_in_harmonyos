# E-draft: const 运行时填充表在 clang 下只读段崩溃（const-table-rodata-segfault）

- 首报：mppenc 1.16 @ OHOS PC aarch64（clang 15.0.4，2026-09-25，主理-30）
- 分类：portability / P1

## 症状
编译全绿；运行任何编码路径（包括 `--quality 5 /dev/null x.mpc`）在 banner 后立即 `Segmentation fault (core dumped)`。编译期另有 `fatal error: 'fpu_control.h' file not found`（同源年代问题，一并修复）。

## 根因
1. `src/fastmath.c` 的四张查找表 `tabatan2/tabcos/tabsqrt_ex/tabsqrt_m` 声明为 `const float` 且**无初始化器**（tentative definition），由 `Init_FastMath()` 运行时填充。
   - 老 gcc：无初始化 const 表 → 可写 `.bss`，历史上侥幸可用；
   - clang：全零 const 对象 → 只读 `.rodata`，首次写入 SIGSEGV。
2. `src/mppdec.h` 按 `__linux__` 包含 glibc 专有头 `fpu_control.h`；bionic 同样定义 `__linux__` 但无此头。真正使用点 `tools.c Init_FPU` 已有 `__i386__ && _FPU_GETCW && _FPU_SETCW` 宏守卫（aarch64 不编译），纯属 include 面。

## 处方
1. 表定义与 extern 声明**成对**去 const（fastmath.c 4 行定义 + mppenc.h 4 行 extern）——示例：`archives/m/mppenc/1.16/patches/0001-src-fastmath.c.patch`
2. glibc 专有头 include 条件加 `defined __GLIBC__`——示例：`patches/0002-src-mppdec.h.patch`（libc 特性判别，非平台宏）
3. 定位手段：鸿蒙 PC ptrace 受限（gdb/lldb 不可用，E046 族）→ `fprintf` 插桩 + 增量重建二分。

## 识别线索
- "编译全绿 + 一运行就段错误 + 崩点在首次写表" ⇒ 优先查 `const` + 运行时填充组合：`grep -n "(float\s*\*)" *.c` 找转型写入的表，再核对定义是否 const。
