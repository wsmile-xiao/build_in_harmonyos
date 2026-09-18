# DRAFT-kissfft-131-ohos-mpil-guard-testcpp：上游测试源编译期引用 M_PIl 的 OHOS 守卫补定义

> Contributor: pc2-36 | Status: Draft | Updated: 2026-09-18
> Source: kissfft 131 HarmonyOS PC 适配（R01，task kissfft-131-r01-pc2-36-20260917T155552Z）
> 本文件与 `DRAFT-kissfft-131-ohos-mpil-guard-testcpp.kv` 配对，stem 完全相同，
> 字段（主题 / error_signature / root_cause / solution / validation / 适用边界）相互对应。

## 现象

kissfft 131 上游测试 `test/testcpp.cc`（C++ 复数 FFT 自检）在 OHOS aarch64 / clang-15 编译失败：

```text
testcpp.cc:46:35: error: use of undeclared identifier 'M_PIl'
        long double phinc = 2*k0* M_PIl / nfft;
                                  ^
1 error generated.
```

## 根因（error_signature / root_cause）

- **M_PIl 缺失**：OHOS musl 系 libc 的 math.h 仅定义 double 常量 `M_PI/M_PI_2/M_PI_4`，
  不定义 long double 的 `M_PIl`；上游测试源码在公式中**直接裸引用** `M_PIl`，
  未包在 `#ifdef M_PIl ... #else` 断言框架内，因此不是"运行期断言失败"，
  而是**编译期 undeclared identifier**。glibc 平台可编译，OHOS 上直接编译失败。

## 方案（solution / rec_approach）

在测试源（C 或 C++）顶部加可移植守卫补定义，值取 glibc M_PIl 同值：

```c
#ifndef M_PIl
#define M_PIl 3.141592653589793238462643383279502884L
#endif
```

要点：
1. 适用于**无 `#ifdef M_PIl` 断言框架**、直接裸引用 M_PIl 的上游测试源；
2. 与 DRAFT-au（gtest `#ifdef M_PIl ... #else ADD_FAILURE()` 运行时断言场景）
   互补：有断言框架→走 au 的 constexpr 常量替换；无框架裸引用→走守卫补定义；
3. 不删除/禁用用例，不修改断言语义，库源码不动。

## 验证（validation）

```bash
# 修复前：clang++ testcpp.cc → error: use of undeclared identifier 'M_PIl'
# 修复后：
clang++ -O2 -D_GNU_SOURCE -I.. -I../tools -o testcpp testcpp.cc -lm   # 编译通过
./testcpp   # float/double/long double 三类型 RMSE 1e-7..1e-31，退出码 0
```

已纳入 kissfft 双口径台账 executed_passed_total=18/18（当前配置可执行集合）。

## 适用边界 / 反例

- 仅限 M_PIl 宏缺失导致的编译失败；
- 若平台同时存在 powl 精度问题（gtest DoubleEq 场景，如 au 0.6.0），须走
  DRAFT-au-0.6.0-ohos-mpil-powl-float-tests 的相对容差方案；
- 若测试源已有 `#ifdef M_PIl` 框架，优先 au 的常量替换法，守卫只是兜底。

## 查重与关系

- 四范围查重：graph/index.tsv 零命中；doc/ 零命中；graph/*.kv 零命中；
  drafts/ 部分命中 DRAFT-au-0.6.0-ohos-mpil-powl-float-tests（同根因、不同触发面）。
- 七轴：exact=false；causal=部分；trigger_overlap=部分（编译期 vs 运行时）；
  solution_overlap=部分（守卫补定义 vs constexpr 替换）；combination_novelty=true；
  boundary_novelty=true；test_migration_novelty=true。
- similar_to: DRAFT-au-0.6.0-ohos-mpil-powl-float-tests
- path: B（知识库扩展；与既有知识存在新增差异，已由本轮真实日志验证）