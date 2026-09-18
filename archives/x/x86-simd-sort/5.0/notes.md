# x86-simd-sort 5.0 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-09-18
- 编译器: clang/clang++ 15.0.4（aarch64-unknown-linux-ohos）
- 状态: built

## 编译步骤

```bash
# 源码: https://github.com/Intel/x86-simd-sort/archive/refs/tags/v5.0.tar.gz
# SHA-256: aca0fd7a334d353f8f2eae44403df45acbdfb4f26061350afa31152f26449937
# 原生探路（tests off）
meson setup builddir --buildtype release && meson compile -C builddir
# Conan 配方构建（ohos-aarch64 profile，含 -Dbuild_tests=true）
conan create archives/x/x86-simd-sort/5.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `lib/x86simdsort.cpp` 编译失败：`__builtin_cpu_supports`/`__builtin_cpu_init` 未声明（20 errors） | x86 专属运行时分派内建在 aarch64 clang 15 上不存在；`-march=haswell` 等探测全 NO，avx2/avx512 目标不构建 | patches/0001-aarch64-scalar-dispatch.patch：用 `#if defined(__x86_64__) \|\| defined(__i386__)` 守卫 check_cpu_feature_support 与 DISPATCH/DISPATCH_KEYVALUE_SORT 的 ISA 选择主体（抽成 XSS_RUNTIME_DISPATCH[_KV] 辅助宏），非 x86 直接解析到既有 scalar 实现 |
| 2 | test_package 运行失败：`Error loading shared library libx86simdsortcpp.so.0` | meson 恒产共享库（libsimdsort 为 shared_library），test_package 运行时 LD_LIBRARY_PATH 未指向包内 lib | 配方 package_info 增加 `runenv_info.prepend_path("LD_LIBRARY_PATH", package_folder/lib)`；test_package 的 test() 以 env="conanrun" 运行消费者二进制 |
| 3 | conan 2.29 无 `meson_layout` / Meson helper 无 `compile()` | OHOS 适配版 conan 2.29.1 API 差异 | layout() 手写 `folders.build="builddir"` + `folders.generators="builddir/generators"`；build() 用 `meson.build()` |
| 4 | meson `dependency('gtest_main')` 找不到 | 本仓 gtest 配方只导出根 gtest.pc，未导出 gtest_main.pc | generate() 中手工生成 gtest_main.pc shim（依赖 gtest.pc + -lgtest_main） |

## 源码修改

- `patches/0001-aarch64-scalar-dispatch.patch`：如上（portability，非 x86 走 scalar）。

## 依赖版本

- gtest/1.17.0（test_requires，build 期测试框架，本仓配方 RREV ab1bc3bf）

## 验证结果

- conan-verify G0-G4 全 PASS（G2 conan create 干净构建 + test_package 消费者用例通过）
- 上游 gtest：90/90 通过（test-qsort.cpp 6 typed tests × 8 类型=48；
  test-keyvalue.cpp 1 × 36 tuple=36；test-objqsort.cpp 1 × 6=6）
- HarmonyOS 专项测试 ohos-test：7/7 通过（scalar 正确性、argsort 置换、qselect、
  partial_qsort、NAN>INF、keyvalue 配对、object_qsort）
- 消费者用例 test_package/test.cpp：qsort + argsort 公开 API 调用，结果与
  std::sort 一致，ALL CONSUMER CHECKS PASSED

## 知识沉淀

- 知识候选台账：reports/knowledge-candidate-ledger.md（C1，路径 B）
- 知识库草稿：knowledge/drafts/DRAFT-x86-simd-sort-aarch64-scalar-dispatch.{md,kv}
  （x86 专属运行时分派内建守卫 + 复用既有 scalar 回退）

## 注意事项

- 本库为 x86-only SIMD 库，OHOS aarch64 上通过 scalar 路径提供完整 API（std::sort
  级语义），不提供 AVX-512 加速；下游若要求 SIMD 性能需在 x86 目标使用。
- meson 恒产 `libx86simdsortcpp.so`，配方以共享库交付；消费者需包内 lib 在
  LD_LIBRARY_PATH（配方已声明 runenv_info）。
---

**编译结束**: 2026-09-18 02:11
**最终状态**: built
