# DRAFT-libalgebra-1.1.0-x86intrin-unconditional-include-guard — 单头文件库无条件包含 x86intrin.h 在 aarch64/OHOS 的守卫方案

- **触发事件**：libalgebra 1.1.0 第一轮 OHOS aarch64 适配（make 阶段 20 errors）
- **路径**：Path B（知识库扩展）
- **编号**：DRAFT-libalgebra-1.1.0-x86intrin-unconditional-include-guard

## 现象

`make -j2`（CMake 项目，aarch64-unknown-linux-ohos clang 15）编译
`benchmark.cpp` 时经 `libalgebra.h:107` 的 `<x86intrin.h>` 级联报错：

```text
libalgebra.h:107 → x86intrin.h → immintrin.h:14:2:
  error: "This header is only meant to be used on x86 and x64 architecture"
  error: invalid input constraint 'a' in asm                     (hresetintrin.h)
  error: use of undeclared identifier '__builtin_ia32_vec_init_v2si' (mmintrin.h)
20 errors generated.
make[2]: *** [CMakeFiles/benchmark.dir/build.make:79: benchmark.cpp.obj] Error 1
```

## 根因

上游 `libalgebra.h` 第 107 行以 `#ifndef _MSC_VER` 为唯一条件无条件包含
`<x86intrin.h>`，仅排除了 MSVC。`<x86intrin.h>` 面向 x86/x64，在 aarch64
clang 15 下内部 `#error` 直接拒绝并级联报 mmintrin/immintrin 相关错误，
导致整个头文件不可编译。

头文件其余代码全部使用 X86_OR_X64 家族宏做平台分支：

```c
#if (defined(__i386__) || defined(__x86_64__) || defined(_M_IX86) || defined(_M_X64))
  #define X86_OR_X64
#endif
```

且第 479 行起已提供 non-x86 回退路径（`STORM_HAVE_BUILTIN_POPCOUNT` →
`__builtin_popcountll`，否则纯整数算法 `STORM_popcount64`）。唯独该
#include 缺失同一架构守卫——修复即把该 include 纳入既有平台宏体系。

## 修复

```c
// libalgebra.h 107-111 行（patches/0001-libalgebra.h.patch，+3/-1）
#if !defined(_MSC_VER) && \
    (defined(__i386__) || defined(__x86_64__) || \
     defined(_M_IX86) || defined(_M_X64))
#include <x86intrin.h>
#endif
```

守卫宏与头文件既有 X86_OR_X64 分支完全同源，未引入新的 `__OHOS__` 平台宏
（符合 R8：patches 默认禁止新增平台宏，本守卫属标准架构可移植性守卫）。

## 验证（真实日志）

| 门禁 | 结果 |
|---|---|
| 头文件 C smoke（`clang -O2 -fPIC -std=c11` + 运行） | exit 0，popcount=64 / intersect=64（reports/step2-header-smoke.log） |
| conan create（ohos-aarch64 profile，G0-G4 + L2/L4/L5） | 全 PASS（reports/conan-verify-report.md） |
| test_package ctest | 2/2：test_libalgebra 0.03s + test_ohos 0.02s（reports/conan-create.log） |

## 适用范围

- 适用：header-only / 单头文件 C/C++ 库在 OHOS aarch64 落地时，头部以弱条件
  包含 x86 专属 intrinsics 头、且库内已有非 x86 回退实现——用头文件既有
  平台宏家族守卫 include 即最小适配，可跨库复用。
- 反例/不适用：库以 x86 SIMD 为功能主体且无 scalar 回退 → 守卫后仍不可用，
  需 NEON 移植或 env_unsupported；编译型库的同类问题属 E005/E016/E506 邻域。

## 关联

- `similar_to`: DRAFT-x86-simd-sort-aarch64-scalar-dispatch（x86 专属代码
  aarch64 守卫，触发面相邻、方案同源；差异：前者是编译型库运行时分派
  `__builtin_cpu_supports`，本条目是 header-only 库头文件无条件 intrinsics include）
- 台账与七轴查重：`archives/l/libalgebra/1.1.0/reports/path-b-candidate.md`