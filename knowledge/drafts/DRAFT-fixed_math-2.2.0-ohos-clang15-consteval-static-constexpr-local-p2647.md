# DRAFT-fixed_math-2.2.0-ohos-clang15-consteval-static-constexpr-local-p2647：OHOS clang 15 未实现 C++23 P2647 —— 合法等价改写 static constexpr→constexpr 修复（fixed_math 37/37 实测验证）

> Contributor: pc4-26 | Status: Draft | Updated: 2026-09-22 (r02 返工更新)
> Source: fixed_math 2.2.0 第一轮完整适配 + r02 返工（OHOS clang 15, aarch64-unknown-linux-ohos）

## 背景

fixed_math 2.2.0 是 header-only C++23 定点数学库（CMake，INTERFACE 目标
`fixed_math`，`target_compile_features cxx_std_23`）。上游单测位于
`unit_tests/`（13 个注册可执行 + 1 个未注册源），测试框架为 boost::ut
（arturbac/ut-ext v2.0.1_5），其中 `unit_tests/include/unit_test_core.h`
提供 `run_consteval_test(fn)` —— 以 C++23 `consteval` 函数在**编译期**执行
测试 lambda。在 HarmonyOS PC 工具链（ohos-sdk_26.0.0.18 native llvm，
clang 15.0.4，`-std=c++2b`）上编译时，r01 有 7 个注册可执行（24 个 `_test` 用例）
报 consteval 常量求值错误；r02 通过**合法等价改写**将全部 37/37 用例修复到
编译、运行、通过（13/13 可执行，exit 0）。

## 现象（r01 首错）

```text
unit_tests/<name>_ut.cc:NN:15: error: call to consteval function 'metatests::run_consteval_test<(lambda ...)>' is not a constant expression
unit_tests/<name>_ut.cc:MM:29: note: control flows through the definition of a static variable
fixed_lib/include/fixedmath/core_ops.h:87:29: note: control flows through the definition of a static variable
      static constexpr auto integral_min{al::min()};
```

涉及可执行（r01 编译失败）：type_convertions_ut（2 处）、subtraction_ut、
misc_functions_ut、sin_cos_ut（2 处）、tan_ut、atan_ut（2 处）。
string_convertion_ut 另因 OHOS libc++ 缺可用 `<format>` 独立失败（见台账 C8/
DRAFT-enchantum-ohos-format-stub，测试环境 shim 修复），不属于本条。

## 根因

C++23 P2647（允许 constexpr/consteval 函数内的 `static constexpr` 局部变量）
在 clang 15 常量求值器中**未实现**（P2647 于 clang 17+ 落地）。当 consteval
测试 lambda 调用的 constexpr 路径含 `static constexpr auto` 局部变量（如
core_ops.h 的 `integral_min`/`integral_max`、math.h sin/cos/tan/atan 实现内
23 处 `static constexpr fixed_internal` 常量）时，求值器报
"not a constant expression / control flows through the definition of a
static variable"。追加 `-fconstexpr-steps=2147483647 -fconstexpr-backtrace-limit=0`
实测仍失败（确认非求值深度/回溯限制），属特性支持缺失。
**关联**：clang 15 亦未实现聚合 CTAD（P1816），`ctx_parse_res{precision, it}`
聚合初始化报 "no viable constructor or deduction guide"（独立最小样例复现），
需显式模板实参。

## 修复（r02 实测，语义等价合法改写）

### 1) P2647 主修复：函数局部 `static constexpr` → `constexpr`

对 consteval/consteval 测试路径内**函数/lambda 局部**的 `static constexpr`
局部变量去掉 `static`。值语义完全一致（均为编译期常量，`static` 仅影响存储
类别；对本用法无可观察差异），C++11+ 即合法，clang 15 常量求值器可正常求值。
**不依赖平台宏、不改任何断言值、不改测试语义、不删用例。**

- 库头：`fixed_lib/include/fixedmath/core_ops.h`（integral_min/max 2 处）、
  `fixed_lib/include/fixedmath/math.h`（23 处）→ 配方补丁 0002/0003
- 测试源：`unit_tests/type_convertions_ut.cc`（approx 2 处）、
  `unit_tests/subtraction_ut.cc`（approx 1 处）→ 配方补丁 0006/0007
- 类成员 `static constexpr`（limits.h numeric_limits 特化、unit_test_common.h
  const_val::value）与静态成员函数（fixed_math.hpp floor）不受影响、无需改。
- 批量规则：仅改"缩进 ≥4 空格的函数局部行"，顶格类成员不动。

### 2) 聚合 CTAD（P1816）修复：显式模板实参

`std_formatter.h`：`return ctx_parse_res{precision, it};` →
`return ctx_parse_res<iterator>{precision, it};`（语义等价）→ 配方补丁 0004。

### 3) `<format>` 缺失（C8，非本条核心）

OHOS libc++ 无可用 `<format>`，按任务许可的最小方案在**测试环境**补忠实 shim
（走库内 formatter/to_string 语义，同 r01 `<source_location>` shim 先例，
不入配方/PR）；registry 有 fmt/ut 制品但 API 面不同（std::format vs fmt::format），
无依赖可恢复。详见 reports/dependency-final-check.md。

## 验证（r02 全量）

- 13/13 注册可执行编译通过（compile_exit=0），运行全部通过（run_exit=0）：
  type_convertions 70 asserts/4 tests、subtraction 37/1、misc_functions 24/3、
  sin_cos 198/2、tan 15/1、atan 293/2、string_convertion 90/4，加 r01 已过的
  6 个（fixed_construction/addition/sqrt/multiplication/division/modulo）。
- **全量通过率 37/37 = 100%**（source_declared_total=37，双口径台账
  reports/upstream-test-ledger.md）。
- 命令：`clang++ -std=c++2b -I <shim> -I unit_tests/include -I fixed_lib/include
  -I <ut-ext>/include unit_tests/<name>_ut.cc <ut-ext>/source/ut.cc -o <name>_ut && ./<name>_ut`
- 对照成立：改写前后唯一差异是 `static` 关键字与 CTAD 显式化，所有断言原样。

## 适用边界 / 反例

- **适用**：任何以 C++23 consteval 运行编译期断言、且被求值路径含函数局部
  `static constexpr` 变量的上游测试框架/库，在 clang 15 工具链上均可采用
  `static constexpr`→`constexpr` 等价改写修复（含 CI）；若同时命中聚合 CTAD，
  补显式模板实参。
- **反例（不适用）**：类成员 `static constexpr`（本就合法）、静态成员函数、
  仅运行期断言（非 consteval）的测试；clang ≥ 17 工具链不触发；错误若来自
  显式 `static_assert`（非常量表达式本身有误）则不是本条目。
- **与 P0960 的区分**：P0960 是聚合括号初始化（`construct_at`/`emplace_back`
  报错），本条目是 consteval 常量求值 + static 局部变量，错误面与修复不同。

## 关系

- similar_to: DRAFT-ohos-clang15-missing-p0960-aggregate-paren-init（同工具链
  C++ 特性缺失大类，不同特性/错误面）；聚合 CTAD 场景 similar_to
  DRAFT-332-openrct2-0.5.3-libcpp15-cpp20-compat（P1816 显式推导指引族）
- caused_by: clang 15 常量求值器未实现 C++23 P2647（关联：未实现聚合 CTAD P1816）
- conflicts_with: 无
- source_event（r02）: fixed_math 2.2.0 r02 返工——24 个编译失败用例经
  等价改写全部真实编译运行通过，37/37=100%；配方补丁 0002-0007 随 PR #11967 交付
