# DRAFT-cudd-3.0.0-optional-sublibs-gate-tests

> Contributor: 2301_76770579 | Status: Draft | Updated: 2026-09-09
> Source: cudd 3.0.0 HarmonyOS PC 适配（可选子库默认关 → 门控一半测试）

## 现象

cudd 3.0.0 默认 `./configure && make check` 只跑 test_ntrv（13 断言），
test_dddmp（7 断言）与 test_obj（2 断言）**静默消失**——不报错、不 SKIP
提示，测试脚本根本没进 TESTS。

## 根因

configure.ac 里 `--enable-dddmp`/`--enable-obj` 默认 no，
`AM_CONDITIONAL(DDDMP/OBJ)` 把这两个子库和它们的测试脚本一起门控掉。
configure 输出末尾的 `dddmp enabled : no / obj enabled : no` 是唯一线索。

## 解决方案

1. configure 显式 `--enable-dddmp --enable-obj`（两者在 OHOS 实测可编可跑，
   无关的理由）→ `make check` 全量 3 脚本 22 断言实跑；
2. MANIFEST 声明上游 N=22 并注明门控关系（防 rule4 少报误判）；
3. 消费侧 BDD 正确性判据用 `Cudd_CountMinterm`（精确满足指派数，与变量
   序无关），不要用 `Cudd_DagSize`（动态重排序后结构可变，判据脆）。

## 禁止策略

- 不得把 13 当作上游测试数上报——那是默认门控后的残缺数。
- 不得用 DagSize==N 做断言——依赖变量序。
- 不得把测试脚本的静默缺失当"环境限制"——先查 AM_CONDITIONAL 门控。

## 适用范围

用 AM_CONDITIONAL 把可选组件与其测试一起门控的 autotools 库：默认
configure ≠ 全量测试覆盖，先看 configure 摘要里的 enabled/disabled 行。
