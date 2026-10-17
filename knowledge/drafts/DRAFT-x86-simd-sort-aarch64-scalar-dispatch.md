# DRAFT-x86-simd-sort-aarch64-scalar-dispatch — x86 专属运行时分派内建在 aarch64/OHOS 缺失时，守卫分派宏并复用既有 scalar 回退

- **触发事件**：x86-simd-sort 5.0 第一轮 OHOS aarch64 适配（conan create 首跑即败）
- **路径**：Path B（知识库扩展）
- **编号**：DRAFT-x86-simd-sort-aarch64-scalar-dispatch

## 现象

conan create（ohos-aarch64 profile）编译 `lib/x86simdsort.cpp` 时报 20 个错误：

```
../lib/x86simdsort.cpp:14:16: error: use of undeclared identifier '__builtin_cpu_supports'
../lib/x86simdsort.cpp:111:9: error: use of undeclared identifier '__builtin_cpu_init'
```

`__builtin_cpu_init`/`__builtin_cpu_supports` 是 x86 专属内建，aarch64 clang 15
（目标 aarch64-unknown-linux-ohos）不存在；同时 `meson setup` 中
`-march=haswell/-march=skylake-avx512/...` 的 `has_argument` 探测全部为 NO，
avx2/avx512 目标库不构建，DISPATCH 宏里 `if constexpr` 分支引用
`&xss::avx512::*`/`&xss::avx2::*` 会产生未定义引用。

## 根因

上游是 x86-only SIMD 排序库（AVX2/AVX-512 intrinsics）。运行时分派通过
constructor 把函数指针初始化为 scalar，再 `__builtin_cpu_init()` + 
`__builtin_cpu_supports()` 探测 ISA 并切换到 avx512/avx2 内核——这一整套
机制只面向 x86。但库自带完整 scalar 回退（`lib/x86simdsort-scalar.h`，
基于 std::sort/nth_element/partial_sort/argsort+permute），只是分派入口
硬依赖 x86 专属内建，导致非 x86 平台连编译都过不去。

## 推荐方案

最小补丁 `patches/0001-aarch64-scalar-dispatch.patch`（不移植 NEON、不改公开 API）：

1. `check_cpu_feature_support()` 函数体用
   `#if defined(__x86_64__) || defined(__i386__) ... #else return 0; #endif`
   守卫——非 x86 恒返回 0，`find_preferred_cpu()` 恒回退 `"scalar"`。
2. 把 DISPATCH / DISPATCH_KEYVALUE_SORT 宏内的 ISA 选择主体抽成条件定义的
   `XSS_RUNTIME_DISPATCH(func, TYPE, ISA)` / `XSS_RUNTIME_DISPATCH_KV(...)`
   辅助宏：x86 展开为原 `__builtin_cpu_init` + 特性分支，非 x86 展开为空，
   所有入口函数指针直接解析到 `xss::scalar::*`，不再引用未编译的 SIMD 符号。
3. meson.build 无需改动：`has_argument('-march=haswell')` 在 aarch64 自然为 NO，
   libtargets 为空，`libsimdsort` 共享库只编 `x86simdsort.cpp`（scalar 路径）。

**验证**：conan-verify G0-G4 全 PASS；上游 gtest 90/90（48 qsort + 36 keyvalue +
6 objsort，typed 实例化口径）；HarmonyOS 专项测试 7/7（scalar 正确性、argsort
置换、qselect、partial_qsort、NAN>INF、keyvalue 配对、object_qsort）；test_package
消费者用例 ALL CONSUMER CHECKS PASSED。

## 适用边界

- 适用：x86-only SIMD 编译型库（运行时分派依赖 `__builtin_cpu_supports`/
  `__builtin_cpu_init`，或 `-march=haswell` 等 x86 march 条件编译）落地
  OHOS aarch64，且库自身已有完整 scalar 回退实现——守卫分派即最小适配。
- 反例：无 scalar 回退、业务语义必须依赖 SIMD 性能的库，或上游测试断言
  特定 ISA 行为（如断言 avx512 内核被调用）的库，守卫分派不适用，需另议。
- 与 DRAFT-jsonifier-neon-cpu-instructions-bits 的区别：jsonifier 是 header-only
  库提交的 CPU 指令集位宏强制包含 immintrin.h/xmmintrin.h（头文件包含问题），
  本条目是编译型库的运行时分派内建（编译期内建缺失问题），且本条目复用
  库内既有 scalar 实现而非改写指令集位。

## 验证/命令

```
conan create archives/x/x86-simd-sort/5.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
# 上游: builddir/testexe --gtest_color=no → 90/90 passed
# 鸿蒙专项: builddir/ohos-test → 7/7 passed
# 消费者: test_package/test_x86-simd-sort → ALL CONSUMER CHECKS PASSED
```
