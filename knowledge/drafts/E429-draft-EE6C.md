# E429 — 单头文件 C 库在 aarch64/OHOS 上三处可移植性缺陷

## 错误特征

```
# 1) x86 专用 SIMD 头在 aarch64 上编译失败
code/zpl.h:530: error: "This header is only meant to be used on x86 and x64 architecture"
#error "This header is only meant to be used on x86 and x64 architecture"

# 2) FILE/tmpfile 未声明（stdio.h 缺失）
code/zpl.h:9939: error: use of undeclared identifier 'FILE'
code/zpl.h:9948: warning: call to undeclared function 'tmpfile'

# 3) posix_memalign 对入参对齐 4 返回 EINVAL，随后断言失败
zpl.h:(9325): Assert Failure: `(ret) != NULL` ret must not be NULL
（dbg 验证：posix_memalign(4,12) rc=22, aligned_alloc(4,12) OK）
```

## 触发条件
- 构建系统: 无（stb 式单头文件库，直接 clang/gcc 编译）
- 阶段: compilation / runtime
- 平台: aarch64（OHOS / ARM Linux）

## 根因分析

zpl 9.8.0 上游三处平台分支缺陷：

1. **x86 SIMD 头无条件包含**：`code/zpl.h` 在
   `#if !defined(ZPL_SYSTEM_ANDROID) && !defined(ZPL_SYSTEM_IOS)` 分支内只排除
   Emscripten 就包含 `<emmintrin.h>`；`#elif defined(ZPL_CPU_X86)` 分支因前置条件
   恒不达。aarch64 上 emmintrin.h/xmmintrin.h 是 x86 专用头，直接编译失败。

2. **stdio.h 条件包含位置**：`<stdio.h>` 仅出现在 Windows 分支、OSX 分支与
   `ZPL_THREADING` affinity 段（`#elif defined(ZPL_SYSTEM_LINUX)`），而
   `ZPL_THREADING` 被上游守卫 `#if !defined(ZPL_SYSTEM_EMSCRIPTEN) && !defined(ZPL_CPU_ARM)`
   在 ARM 上禁用 → 主头从未包含 stdio.h，`FILE`/`tmpfile()` 未声明。

3. **heap allocator 分支不一致**：x86 Linux 用 `aligned_alloc`，ARM Linux
   （`#elif defined(ZPL_SYSTEM_LINUX) && !defined(ZPL_CPU_ARM)` 未命中时落入 else）
   误用 `posix_memalign(&ptr, alignment, size)`；`zpl_base64_decode` 以对齐 4 分配，
   POSIX 要求对齐为 `sizeof(void*)` 倍数且 2 的幂，`posix_memalign(4)` 返回 EINVAL
   （rc=22）→ 分配返回 NULL → 断言失败。

## 解决方案

### 推荐方案（归档补丁 patches/0001-zpl-h-aarch64-portability.patch）
1. SIMD 头只在 `ZPL_CPU_X86 && !ANDROID && !IOS && !EMSCRIPTEN` 时包含，否则 `#include <sched.h>`。
2. 主头非 Windows 包含区（`#include <math.h>` 之后）无条件补 `#include <stdio.h>`。
3. ARM Linux 与 x86 Linux 一致使用 `aligned_alloc`（条件改为 `#elif defined(ZPL_SYSTEM_LINUX)`）。

### 禁止做法
- ❌ 不删除 SIMD 功能代码（仅改包含条件，保留 x86 上的 emmintrin 路径）。
- ❌ 不修改 ZPL_THREADING 的 ARM 排除守卫强行启用线程（上游原子操作未实现，`#error TODO: Implement Atomics for this CPU`）。
- ❌ 不把 `/tmp` 只读导致的 tmpfile 失败当库缺陷（平台限制，用 TMPDIR + zpl_file_open 等价验证）。

## 验证
```bash
# 修复前（仅 1/29 编译通过；base64 断言失败 SIGTRAP rc=133）
clang -I<src> -I<src>/code -std=gnu99 -O1 -o base64 test/base64.c
# 修复后：24/29 编译通过；base64 rc=0；鸿蒙专项测试 ALL OK rc=0
clang -I<src> -I<src>/code -std=gnu99 -O1 -o test_harmonyos test_harmonyos.c && ./test_harmonyos
```

## 关联条目
- 相关: E476（OHOS musl 分配对齐不足——触发边界不同：E476 是"返回对齐不足"，
  本条目是"posix_memalign 拒绝小对齐入参"，修复方向相反）
- 来源: zpl 9.8.0 适配（task zpl-9.8.0-r01-pc2-34）
