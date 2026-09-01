# DRAFT-gcem-1.16.0-ohos-libm-long-double-boundary：OHOS long double libm 参考边界诊断

> Contributor: junshi_liu (兰州大学DSLab) | Status: Draft | Updated: 2026-08-31
> Source: gcem 1.16.0 HarmonyOS PC 适配（R02，task gcem-1.16.0-r02-...-20260831T000741Z）
> 本文件与 `DRAFT-gcem-1.16.0-ohos-libm-long-double-boundary.kv` 配对，stem 完全相同，
> 字段（主题 / error_signature / root_cause / solution / validation / 适用边界）相互对应。

## 现象

gcem 1.16.0 上游测试 `tests/` 共 43 个入口全部编译并运行（OHOS aarch64 / clang-15 工具链），
40 个通过；`log`、`log10`、`log2` 三个入口在 `<each>` 相同的用例上失败：

```text
Test number: 8 - Function Call: gcem::log(1e-500);
Expected value: -inf;  Actual value: -1151.29
libc++abi: terminating due to uncaught exception of type std::runtime_error: test fail
Signal 6 (core dumped)
```

三个失败共用同一用例：`GCEM_TEST_COMPARE_VALS(gcem::log, std::log, 1e-500L)`（log10/log2 同参数）。

## 根因（error_signature / root_cause）

- OHOS aarch64 / clang-15 平台上 `sizeof(long double) = 16`（IEEE-754 quad），
  `LDBL_MIN = 0x1p-16382`，因此 `1e-500L` 是完全**正常**、可表示的值
  （≈ `0x1.0675b44007b734ff1d9a8873b40ap-1661`），不是 subnormal。
- 探针证实平台参考实现 `std::log(long double)` 在该"极小正常 quad 域"发生下溢误判：
  `std::log(0x1p-1600L) = -inf`，而控制值 `std::log(2.0L) = 0.693147`、
  `std::log(1e5L) = 11.5129` 均正常。
- gcem 以自身连分式 / 尾数展开计算，返回数学上正确的有限值 `-1151.29`（= ln(1e-500)）。
- 上游测试将"库值"与"平台参考 oracle"对比：期望 `-inf`、实际 `-1151.29`，以
  `std::runtime_error` 中止（SIGABRT）。
- 因此该不一致是 **OHOS libm long double 边界行为**，**不能归因为 gcem 计算错误**。

## 方案（solution / rec_approach）

可复用的比较策略：对极小 `long double` 域先验证参考实现可用性 / 有限性与类型语义，
再把"库值与异常参考值不一致"分离为平台 libm 边界记录：

1. **确认类型语义**：`sizeof(long double)` 与 `LDBL_MIN`（OHOS：quad、0x1p-16382，
   故 1e-500L 为正常值）。
2. **在失败点探测参考实现**：`std::log(0x1p-1600L) == -inf`，并加邻近有限控制值
   （`std::log(2.0L)`、`std::log(1e5L)`）。
3. **独立验证库值**：gcem 的 -1151.29 数学上等于 ln(1e-500)。
4. **判定与记录**：参考异常、库值正确 → 记为平台 libm long double 边界记录：
   保留用例可运行、如实记录 expected/actual、归属 OHOS libm、不阻塞库质量结论。
5. **禁止动作**：不得放宽断言、删除用例、伪造通过，也不得宣称"已修复 OHOS libm"。

## 验证（validation）

- gcem 1.16.0 R02：43 入口编译运行，40 通过；log/log10/log2 失败于 `1e-500L` 用例。
- 探针证据：`sizeof(long double)=16`；`1e-500L` 为正常 quad 值；
  `std::log(0x1p-1600L)=-inf` 而 `std::log(2.0L)`、`std::log(1e5L)` 正确；
  gcem 值 -1151.29 与 ln(1e-500) 一致。
- 原始运行日志 SHA-256：`e1ddfc022fcb065d623489f60fb6bd338b63f68f16cee54314ec04e1a35202e8`。
- 结论：平台 libm 边界；gcem 行为正确；未修改 gcem 源码；台账归档于
  `archives/g/gcem/1.16.0/reports/upstream-test-ledger.md`。

## 适用边界（affected_scope / rec_edges）

- 适用：OHOS aarch64/clang-15 上，任何把 constexpr 或自实现数学结果与 `std::`/libm
  long double 参考值在**极小正常域**（约 < 1e-300 的 long double）对比的上游测试；
  header-only 编译期数学库（gcem 及同类 constexpr 数学代码）的 log/log10/log2/exp 族
  边界用例最易触发。
- 不适用：普通构建失败、网络等待、远端服务不可达（那些不属于此诊断模式）；
  若参考实现与库值均为有限且接近，仍属普通数值误差处理。
- 查重差异：正式索引 E277（vendored 依赖构建/staging）、E305（字体资源包）、
  E312（groonga 上游测试框架链）、musl-glibc 全量接口表、drafts 均**无** long double
  libm 参考边界诊断条目；本条目为增量，不重复既有知识。