# E999: OHOS musl long double 数学函数族为 double 精度别名

> Draft: DRAFT-E999-ohos-musl-long-double-double-alias
> 来源：boost1.84-math/1.84.0 适配（PR #8441），2026-09-05

## 现象

boost.math 官方测试 `libs/math/test/test_tr1.c` 的 TEST_LD 模式
（long double 断言 269 项）在 OHOS aarch64 上 95 项失败，报错形如：

```text
Error at line 740, with error 3.330669e-16 (max allowed 9.629650e-33)
```

失败误差量级全部在 ~1e-16（double 精度特征），而容差是
LDBL_EPSILON × N ≈ 1e-30 量级（quad 精度期望）。

## 根因

OHOS musl libc 的 `*l` 后缀数学函数族（coshl/powl/sinhl/expl/logl/
atanhl...）与对应 double 版本是**同一地址的别名 stub**：

```bash
nm -D $OHOS_SDK/sysroot/usr/lib/aarch64-linux-ohos/libc.so | grep -wE 'cosh|coshl|pow|powl'
# 0000000000011d80 T cosh
# 0000000000011d80 T coshl     ← 同一地址
```

而 aarch64 clang 的 long double 类型是 IEEE quad：

```text
sizeof(long double)=16, LDBL_MANT_DIG=113, LDBL_EPSILON=1.925930e-34
```

编译器侧是 quad、libc 侧是 double 别名——任何依赖 libc `*l` 函数返回值
做 quad 精度断言的测试都会失败，**非适配缺陷而是平台实现限制**。

## 判定方法（可机器匹配）

1. 打印 long double 特性：`LDBL_MANT_DIG=113` → 编译器是 quad
2. nm -D 对比 `*l` 与 double 版本符号地址：相同 → libc 是别名
3. 两者同时成立 = 命中本模式

## 处置建议

- 库照常编译交付（符号/ABI 完整，double/float 精度范围可用）
- long double 测试失败项如实记录为平台限制（notes.md + PR 豁免说明）
- 下游需要真 quad 精度：绕开 libc `*l` 函数族，改用模板 header-only
  实现直接实例化 long double（boost::math special_functions 内部软件实现
  不经 libc）

## 实例数据

- boost1.84-math 1.84.0：TEST_LD 95/269 失败全部归因此模式；
  普通模式（float/double 538 断言）100% 通过

## 降级方案（fallback）

- 库功能依赖真 quad 精度（不容降级）→ 绕开 libc `*l` 函数族，改用库的
  模板 header-only 实现直接实例化 long double（boost::math 内部软件浮点
  不经 libc）
- 比赛要求逐项全绿且无法豁免 → 只跑 float/double 段并显式 skip `*l` 段
  （记录原因），不做假通过
- SDK 版本演进后重跑一次 nm 验证即可判定是否有真实现

## 证据链（PR !8441）

| 证据 | 内容 |
|------|------|
| nm 实证 | coshl/cosh 同地址 0x11d80（powl/pow、sinhl/sinh 同） |
| 编译器特性 | LDBL_MANT_DIG=113、LDBL_EPSILON=1.925930e-34（IEEE quad） |
| 失败断言分布 | 95 项误差全部 ~1e-16（double 特征）vs 容差 ~1e-30（quad） |
| 上游测试 | test_tr1.c 普通模式 538/538=100%；TEST_LD 174/269（95 项平台限制豁免） |
| 处置 | libboost_math_{tr1l,c99l}.a 照常交付（符号/ABI 完整）；notes.md 问题 4 + PR 正文豁免说明 |
| CI | #40551 / #40565 全绿 |
