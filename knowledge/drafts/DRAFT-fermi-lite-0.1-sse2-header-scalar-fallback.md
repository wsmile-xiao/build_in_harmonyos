# DRAFT-fermi-lite-0.1: 无条件包含 x86 专属 SIMD 头导致 aarch64 编译失败，需条件编译 + 标量回退

## 症状

`make CC=clang` 在 aarch64（OHOS 真机）上编译 `ksw.c` 立即失败，报错来自 clang 自带头：

```
/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/clang/15.0.4/include/emmintrin.h:14:2: error: "This header is only meant to be used on x86 and x64 architecture"
```

随后是一大批 `mmintrin.h` 的 `__m64`/vector 类型错误（`invalid conversion between vector type ... and integer type`），最后 `fatal error: too many errors emitted`。

## 根因

上游 `ksw.c`（2011 年 Attractive Chaos 的 ksw，fermi-lite 0.1 内嵌使用）第 28 行**无条件** `#include <emmintrin.h>`，且核心对齐核（`ksw_qinit`/`ksw_u8`/`ksw_i16`）全部用 `__m128i` SSE2 内建函数实现，**没有任何标量回退**。x86 专属头在 aarch64 上被 clang 直接拒绝——这是编译期错误，不是链接期缺失，知识库中既有 SIMD 条目（E100/E506/png NEON 源选择等）都属于链接期 undefined symbol 或编译器能力探测，与本模式不匹配。

## 方案

给 `ksw.c` 增加 `#if defined(__SSE2__)` 条件编译：

- `#if defined(__SSE2__)` 分支：原 SSE2 实现原样保留（x86 行为不变）；
- `#else` 分支：提供等价的**标量**（逐单元 DP）`ksw_qinit`/`ksw_u8`/`ksw_i16`，对内存布局做同样的 16 字节对齐分配，score 用 `KSW_CLAMP8/KSW_CLAMP16` 复刻 `_mm_*s_epu8/16` 的饱和加减语义，`ksw_align` 复用不变。

配套补丁：`rle.h` 中 `const uint8_t rle_auxtab[8];` 属头文件内 tentative definition，多 TU 包含后在 clang 默认 `-fno-common` 下产生 **duplicate symbol: rle_auxtab** 链接错误，需改为 `extern const uint8_t rle_auxtab[8];`（定义保留在 rle.c）。

## 验证

1. `make CC=clang AR=llvm-ar -j1` 编译通过，生成 `libfml.a` 与 `fml-asm`；
2. 上游冒烟：`./fml-asm test/MT-simu.fq.gz > MT.fq`（退出码 0，输出 2 条 unitig fasta）；
3. conan create（ohos-aarch64 profile）→ test_package 调用 `fml_assemble()` 实际组装 API，n_utg=2、ok=1 通过；
4. conan-verify G1/G2/G3/G4 + L2/L4/L5 全绿。

## 适用边界与限制

- 适用于**纯 C 老代码直接包含 x86 专属 SIMD 头且无标量回退**的场景；若上游已有 NEON 分支，优先走 NEON 而非标量。
- 标量 DP 与 SSE2 在数值语义上通过饱和算术对齐，但对超大输入性能低于 SIMD（fermi-lite 组装场景在 aarch64 上可接受）。
- ksw 的 `#else` 分支只应交付给 aarch64 消费；x86 构建必须走原 SSE2 代码，不能因条件编译改变 x86 产物。

## 反例

- 不能把 `-D__SSE2__` 或忽略错误当作修复（aarch64 上 emmintrin.h 依然拒绝编译，忽略错误只会得到损坏产物）；
- 不能让非当前库的 CMake/处理器字符串判断（如 E506 的 `CMAKE_SYSTEM_PROCESSOR`）替代编译器能力事实。