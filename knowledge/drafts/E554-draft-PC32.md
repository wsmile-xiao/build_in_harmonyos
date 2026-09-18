# E554 — clang -O2 常量折叠使 FPCR.FZ/DAZ 运行时控制对已折叠常量失效

> Draft: E554-draft-PC32
> 来源：sse2neon 1.9.1 适配（ieee754 上游测试），2026-09-16

## 错误特征

sse2neon 上游测试 `tests/ieee754` 在 OHOS aarch64 + clang 15 下以 `-O2`
编译运行时，FTZ/DAZ 相关用例失败：

```text
Test ftz_output_flush                    [FAIL]
Test daz_input_flush                     [FAIL]
Results: 47 passed, 2 failed, 0 skipped
```

同一测试以 `-O0` 编译则 49/49 全部通过。

## 触发条件

- 构建系统: Makefile（clang++ -O2，`-march=armv8-a+fp+simd`）
- 阶段: testing（运行时 CSR 控制依赖型用例）
- 触发模式: 测试先 `_mm_setcsr(_MM_FLUSH_ZERO_ON)`（写 ARM FPCR.bit24），
  再对**编译期常量**（`FLT_MIN * 0.5f`）做 SIMD 乘法并断言结果被 flush 为 0

## 根因分析

clang `-O2` 在编译期将 `FLT_MIN * 0.5f` 常量折叠为次正规常量
（5.87747e-39），运行时 FPCR.FZ/DAZ 位只作用于实际执行的浮点指令，
对已在编译期折叠进立即数的常量无作用，因此断言失败。

**平台 FZ 本身有效**——裸 asm 置 FPCR.FZ 后，对运行时输入做标量
`fmul` 与 NEON `vmulq_f32` 实测均正确 flush 为 0（见验证）。故这是
编译器常量折叠 × 运行时 CSR 控制的交互，非 OHOS 平台缺陷。

## 解决方案

### 推荐方案

- 诊断：同一 FTZ 测试分别以 `-O0` 与 `-O2` 编译对照；`-O0` 通过而
  `-O2` 失败即命中此模式。
- 验证平台 FZ 有效性：裸 asm `mrs/msr FPCR` 置 bit24（FZ）后，对
  运行时输入执行 `fmul` / `vmulq_f32`，结果应为 0。
- 处置：此类上游测试如实记录为「优化敏感性」，`-O0` 下全过即平台
  能力达标；不修改上游测试、不打补丁伪造通过。
- 下游指引：业务代码依赖运行时 CSR（FZ/DAZ/舍入模式）控制时，注意
  编译器常量折叠会绕过运行时控制，必要时用 `volatile` 或运行时输入。

### 禁止做法

- ❌ 修改上游测试把失败项直接断言为通过
- ❌ 以 -O2 失败为由误判为 OHOS 平台缺陷而停止交付

## 验证

```bash
# 1) -O0 全过 / -O2 有 2 项失败（sse2neon ieee754）
clang++ -O0 -I. -march=armv8-a+fp+simd tests/ieee754.cpp tests/common.cpp tests/binding.cpp -lm -o /tmp/ieee754-O0 && /tmp/ieee754-O0   # 49 passed
# 2) 裸 asm 验证平台 FZ 有效（标量与 NEON 均 flush）
#    msr FPCR 置 bit24 后：scalar fmul = 0；neon vmulq runtime input = 0
```

## 关联条目

- 相关: E555（同源 clang 优化行为差异）
