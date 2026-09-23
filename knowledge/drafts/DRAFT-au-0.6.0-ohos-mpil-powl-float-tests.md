# DRAFT-au-0.6.0-ohos-mpil-powl-float-tests：OHOS 上 M_PIl 缺失与 powl 精度的上游浮点测试移植

> Contributor: junshi_liu | Status: Draft | Updated: 2026-09-03
> Source: au 0.6.0 HarmonyOS PC 适配（R01，task au-0.6.0-r01-pc1-27-20260903T013832Z）
> 本文件与 `DRAFT-au-0.6.0-ohos-mpil-powl-float-tests.kv` 配对，stem 完全相同，
> 字段（主题 / error_signature / root_cause / solution / validation / 适用边界）相互对应。

## 现象

au 0.6.0 上游测试（gtest/gmock，OHOS aarch64 / clang-15）全量 1824 项中 3 项失败：

```text
[  FAILED  ] Pi.HasCorrectValue          -> ADD_FAILURE: M_PIl not available on this architecture
[  FAILED  ] GetValue.PiToThePower1HasCorrectValues  -> 同上
[  FAILED  ] Root.ResultIsVeryCloseToStdPowForPureRoots
             Expected: is approximately 384173749.49624783
               Actual: 3.84174e+08 (of type double)
```

第三项为 x=5.67e25, r=3 的立方根比较：au root 二分搜根得 384173749.4962483，
std::pow(x, 1.0L/r) 得 384173749.49624783，绝对差 4.77e-07（相对 1.24e-15），
超出 gtest `DoubleEq`（4*DBL_EPSILON ≈ 8.9e-16 相对）的容差。

## 根因（error_signature / root_cause）

- **M_PIl 缺失**：OHOS libc（musl 系）头文件不定义 `M_PIl`；上游测试以
  `#ifdef M_PIl ... #else ADD_FAILURE()` 模式编写，在有 M_PIl 的平台上运行，
  移植到 OHOS 时无条件失败（构建不受影响，属测试可移植性假设）。
- **powl 精度**：OHOS libm 的 `std::pow(long double)` 在普通 double 值域有约
  1e-15 相对误差；au 自身的 `root()` 以 128 位 quad long double 二分搜根，
  反而更接近真值。高精度探针：au=384173749.4962483（距真值 2.3e-08）、
  powl=384173749.49624783（距真值 4.5e-07）。因此失败源于"参考实现 powl 的
  精度劣于被测库"这一平台特性，而非库缺陷。

## 方案（solution / rec_approach）

可复用的浮点测试移植策略：

1. **M_PIl 缺失**：在测试文件定义可移植常量
   `constexpr long double kPiLongDouble = 3.141592653589793238462643383279502884L;`
   （与 glibc M_PIl 同值），`#else` 分支以该常量比较替代 `ADD_FAILURE()`。
2. **powl 精度**：把 `DoubleEq(std::pow(x, 1.0L/r))` 改为
   `DoubleNear(expected, kRelativeTolerance * |expected|)`，取相对容差 1e-12
   （远严于 float 精度 1e-7，且 au 值本身正确）。先量化 absdiff 与 rel diff，
   再选容差，避免随意放宽。
3. **禁止动作**：不得删除/禁用用例、不得伪造通过、不得把失败写成库缺陷；
   修复只作用于测试断言的平台可移植性，库源码不改。

## 验证（validation）

- au 0.6.0 R01：3 项修复后 magnitude_test 单独通过；全量 ctest -j1 串行
  1824/1824 = 100%（日志 au-r01-ctest-serial-r2.log）。
- 探针证据：`sizeof(long double)=16`（quad）；powl vs au root 差异量化见上；
  char signed=0（arm64 char 默认 unsigned）。
- 原始日志 SHA-256：见任务 result（au-r01-ctest-serial-r2.log 等，逐项提供）。
- 结论：M_PIl 缺失与 powl 精度均属平台测试可移植性；以等值常量 + 相对容差修复；
  未修改库源码（仅测试文件），台账归档于 `archives/a/au/0.6.0/reports/`。

## 适用边界（affected_scope / rec_edges）

- 任何 OHOS/arm64 上消费 `M_PIl` 的上游 C/C++ 测试；
- 任何以 gtest `DoubleEq`/严格 ULP 断言比较 libm 参考值（powl 路径）或
  root/二分实现 vs `std::pow` 的上游测试；
- 不适用于 glibc（x86_64/aarch64 Linux）等 powl 精度正常的平台；
  该平台若出现同类失败，应优先排查库自身算法而非套用本容差。

## 查重差异

- DRAFT-gcem-1.16.0-ohos-libm-long-double-boundary：覆盖 OHOS long double libm
  参考边界，但聚焦极端小 normal 域下溢（std::log(1e-500L)=-inf）；本候选为
  头文件常量缺失 + 普通域 powl 相对误差 + gtest 容差语义，根因/入口不同。
- E388（Boost.Math promote double）、E455（conan libcxx）、E363（shell 误绿）：
  主题不同，非覆盖。