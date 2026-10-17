# E257 — OHOS extended-precision math oracle is non-finite for finite inputs

> 路径 B 知识库扩展草稿；最终编号、是否纳入正式图谱及分值由知识库主编和赛事评审决定。

## 问题模型

HarmonyOS PC aarch64 的 `long double` 为 16 字节扩展精度，能够表示
`1e-500L` 和 `std::numeric_limits<long double>::min()`（设备实测最小值约为
`3.36e-4932`）。但设备 libc 对以下六个调用返回 `-inf`：

| 上游文件 | 输入 | 参照调用 |
| --- | --- | --- |
| `tests/log.cpp` | `1e-500L` | `std::log` |
| `tests/log.cpp` | `numeric_limits<long double>::min()` | `std::log` |
| `tests/log10.cpp` | `1e-500L` | `std::log10` |
| `tests/log10.cpp` | `numeric_limits<long double>::min()` | `std::log10` |
| `tests/log2.cpp` | `1e-500L` | `std::log2` |
| `tests/log2.cpp` | `numeric_limits<long double>::min()` | `std::log2` |

这些值在输入端可表示，问题出在系统标准库参照值非有限。直接把库的结果与该参照值比较，会把“oracle 无效”错误归类为库实现失败。

## 诊断与处理

1. 在目标设备读取 `sizeof(long double)`、`digits`、`min()` 和 `max()`。
2. 对每一个候选边界输入调用标准库参照函数，记录输入、输出和 `std::isfinite` 结果。
3. 只对参照值非有限的精确 case 做显式 skip，输出包含函数名和输入的可检索标记；其他比较和测试程序继续执行并保留退出码。
4. 用普通有限范围输入的独立 consumer 检查，以及其余完整上游程序，验证库算法。若库结果本身错误，必须修复或如实保留失败，不能套用本条目。

## gcem 实证

gcem 1.18.0 上游 CMake 注册 46 个测试程序，没有 CTest case，因此配方实际构建并启动全部 46 个程序。补丁仅在上述六个 `std::log*` 参照调用非有限时输出 `GCEM_UPSTREAM_TEST_CASE_SKIP=... reference is not finite`；没有删除测试程序，也没有改变其他断言。

设备日志 `/storage/Users/currentUser/tmp/gcem-1.18.0-87aa6cb-create.log` 中，`log.test`、`log10.test`、`log2.test` 各输出两个对应 skip 标记；46/46 程序实际启动并通过，程序级失败为 0。`test_package` 的 long-double `log(0.1L)`、`incomplete_beta` constexpr 和运行时检查继续通过，说明跳过的是无效系统 oracle，不是整个 long-double 功能面。

同一适配还分别修复了 `find_exponent.hpp` 的 long-double 字面量精度和小输入 `sqrt` 的 Newton 缩放；这两项是真实库算法问题，不能与六个 oracle skip 混为一谈。

## 可复用范围

适用于 OHOS aarch64 或其他扩展精度 ABI/libc 组合下，数值库上游测试把系统 `libm`/`libc` 结果当作极小值 long-double oracle 的场景。它提供的是“先证明 oracle 有效性，再决定是否跳过”的测试证据边界，不是通用失败豁免。

## 查重差异

已有 `DRAFT-quantlib-boost-math-long-double-promotion` 描述 Boost.Math 的 double-to-long-double promotion 导致数值算法不收敛；本条目不覆盖 promotion，新增的是设备 libc 对可表示 extended-precision 输入返回非有限 reference 的诊断、逐 case guard、日志要求和独立 consumer 回归方法。

## 禁止做法

- 不得用 `|| true`、忽略退出码或全量禁用测试掩盖真实失败。
- 不得把库实现结果强行改为 `-inf` 来迎合无效 reference。
- 不得把六个精确 case 的 skip 扩展为整个 `log`、`log10`、`log2` 程序跳过。
