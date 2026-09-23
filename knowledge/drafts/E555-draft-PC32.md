# E555 — clang aarch64 下 (int64_t)NaN float→int64 转换在 -O2 为 UB 生成垃圾值

> Draft: E555-draft-PC32
> 来源：sse2neon 1.9.1 适配（nan 上游测试），2026-09-16

## 错误特征

sse2neon 上游测试 `tests/nan` 在 OHOS aarch64 + clang 15 下以 `-O2`
编译运行时，NaN→int64 标量转换用例失败：

```text
FAILED: res == indefinite || res == 0 (line 1753)
Test cvtss_si64_nan                           [FAIL]
Results: 130 passed, 1 failed, 0 skipped
```

同一测试以 `-O0` 编译则 131/131 全部通过（`(int64_t)NaN` 返回 0，符合
上游允许值 `res == indefinite || res == 0`）。

## 触发条件

- 构建系统: Makefile（clang++ -O2，`-march=armv8-a+fp+simd`）
- 阶段: testing（标量 float→int64 转换）
- 触发模式: `static_cast<int64_t>(float NaN)`——C++ 标准规定
  float→int64 的 NaN 转换是未定义行为

## 根因分析

sse2neon `_mm_cvtss_si64` 实现为 `static_cast<int64_t>(float_lane)`。
C++ 中 `(int64_t)NaN` 是未定义行为：

- clang aarch64 `-O2`：实测返回垃圾值（370999932605、543919170456 等，
  非 0、非 INT64_MIN）
- clang aarch64 `-O0`：实测返回 0（符合上游对 ARM 的允许语义）
- x86 硬件：返回 INT64_MIN（Integer Indefinite）

同源现象：裸 asm `fcvtas x0, %s1`（round-to-nearest float→int64）在
本机对 NaN 输入触发 Signal 11（SIGSEGV），说明 OHOS aarch64 上该转换
路径受浮点异常/代码生成影响，行为不可依赖。

## 解决方案

### 推荐方案

- 诊断：同一 NaN 转换分别以 `-O0` 与 `-O2` 编译复现；`-O0` 返回 0 而
  `-O2` 返回垃圾值即命中。
- 处置：依赖 NaN→int64 结果的业务代码必须显式 `isnan/isfinite`
  守卫，或使用饱和转换指令（如 `vcvtq_s64_f64` 的饱和语义），不得依赖
  `static_cast` 对 NaN 的结果。
- 适配库层面：上游测试失败项如实记录为「编译器 UB 代码生成差异」，
  `-O0` 通过即满足上游允许语义；不打补丁伪造通过。

### 禁止做法

- ❌ 依赖 `(int64_t)NaN` 的具体返回值（UB，编译器/优化级别间不可移植）
- ❌ 以 -O2 失败为由误判为 OHOS 平台缺陷而停止交付

## 验证

```bash
# 1) -O0 全过 / -O2 有 1 项失败（sse2neon nan）
clang++ -O0 -I. -march=armv8-a+fp+simd tests/nan.cpp tests/common.cpp tests/binding.cpp -lm -o /tmp/nan-O0 && /tmp/nan-O0   # 131 passed
# 2) 最小复现
#    (int64_t)NaN @ -O0 = 0 ; @ -O2 = 垃圾值（实测 370999932605 等）
```

## 关联条目

- 相关: E554（同源 clang 优化行为差异）
