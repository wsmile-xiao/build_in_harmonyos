# DRAFT-x86-simd-only-c-library-aarch64-scalar-fallback — x86-only SIMD C 库（#error 强制且无内置回退）在 aarch64/OHOS 落地：新增标量回退 + 条件含 immintrin.h + 测试框架移植

- **触发事件**：faster-utf8-validator cf482014d0 第一轮 OHOS aarch64 适配（编译即败）
- **路径**：Path B（知识库扩展）
- **编号**：DRAFT-x86-simd-only-c-library-aarch64-scalar-fallback

## 现象

conan-verify / clang 直接编译 `z_validate.c`（aarch64-unknown-linux-ohos）时报错：

```
/data/.../llvm/lib/clang/15.0.4/include/immintrin.h:14:2:
error: "This header is only meant to be used on x86 and x64 architecture"
#error "This header is only meant to be used on x86 and x64 architecture"
z_validate.c:...: error: 'size_t' undeclared
z_validate.c:...: error: unknown type name '__m256i'
```

上游 `z_validate.c` 结构：`#if defined(AVX2) ... #elif defined(SSE4) ... #else #error
"No valid configuration: must define one of AVX2 or SSE4" #endif`，且顶部无条件
`#include <immintrin.h>`；`size_t` 依赖 immintrin 传递引入。

## 根因

1. 上游是 x86-only SIMD 单文件 C 库（AVX2/SSE4 intrinsics），以 `#error` 强制二者之一，
   无任何非 x86 路径；aarch64 clang 15 连 immintrin.h 都没有 → 编译直接失败。
2. 库无内置标量回退 → 只能从零实现一个语义等价（拒绝 overlong/代理对/超 U+10FFFF/截断/
   游离续字节）的标量 `z_validate_utf8`，并把向量实现整段守卫进
   `#if defined(AVX2)||defined(SSE4)`。
3. immintrin.h 条件包含后 `size_t` 缺声明 → 显式补 `<stddef.h>`。
4. 上游测试 `test.lua` 依赖 LuaJIT `ffi` 加载 `_out/avx2/rel/zval.so`、
   `_out/sse4/rel/zval.so` 并调用 `z_validate_utf8_avx2/_sse4`——aarch64 无 LuaJIT
   且无法构建 x86 SIMD .so → 按恢复规则把 46 项独立用例移植为 C 测试目标实际运行。

## 方案

1. `z_validate.c`：`#else #error` 分支改写为完整标量实现；向量部分加
   `#if defined(AVX2)||defined(SSE4)` 守卫；`immintrin.h` 条件包含；补 `<stddef.h>`。
2. 新增 `CMakeLists.txt`（构建 libzval.a + 安装公共头 `z_validate.h`）+ 测试目标。
3. 新增 `test_ohos_special.c`（鸿蒙专项：真实 CJK/emoji/业务文本 + 边界拒绝 + 长输入）。
4. 新增 `test_upstream_port.c`（上游 46 项声明用例移植，含帧移动/尾部填充同构复刻逻辑）。
   x86 上仍可 `-DAVX2/-DSSE4` 走原 SIMD 路径，双路径共存。

## 验证

- 冒烟：18 例（6 合法 + 12 非法）0 失败
- 上游 46 项移植：46/46，127,803 次校验，0 失败（`checks=127803 fails=0`）
- 鸿蒙专项：22/22（ctest 100%）
- 消费者：`consumer_verify.c` accepted=3 rejected=2，exit 0
- conan-verify G1-G4/L2/L4/L5 全部 PASS；W3 本地 CI 模拟通过；finish EXIT_CODE 0

## 适用边界 / 反例

- 适用：纯 C/C++ 单文件或小源集库，x86 SIMD 为唯一实现、允许标量语义等价、测试框架
  （LuaJIT 等）目标平台不可用
- 反例：业务强依赖 SIMD 性能 → 应走 NEON 移植（E506 方向）；已有标量回退仅分派缺内建 →
  按 DRAFT-x86-simd-sort-aarch64-scalar-dispatch；header-only 宏位驱动 → 按
  DRAFT-jsonifier-neon-cpu-instructions-bits

## 查重差异（七轴）

- exact_duplicate=false；causal_duplicate=部分（x86-only SIMD/immintrin 两邻草稿）
- trigger_overlap：与 jsonifier 草稿高度重叠（同 immintrin 报错行）
- solution_overlap=部分（x86-simd-sort 为"已有 scalar 仅守卫分派"；本条目为"#error 强制且
  **从零实现标量**"）
- combination_novelty / boundary_novelty / test_migration_novelty = 新增（纯 C 单文件形态 +
  测试框架整体移植）

## 关系

- similar_to: DRAFT-x86-simd-sort-aarch64-scalar-dispatch
- similar_to: DRAFT-jsonifier-neon-cpu-instructions-bits
- caused_by: none / prerequisite_of: none / conflicts_with: none