# DRAFT-cuba-4.2.2-no-testsuite-demo-as-l1

> Contributor: 2301_76770579 | Status: Draft | Updated: 2026-09-09
> Source: cuba 4.2.2 HarmonyOS PC 适配（无测试套件数值库，demo 作 L1）

## 现象

Cuba 4.2.2（feynarts.de，数值积分库）**没有 `make check` 正式测试套件**：
`makefile.in` 无 check/test 目标，唯一的 `testsuite.m` 是 Mathematica 脚本
（本目标不可运行）。规则 4 要求上游测试数如实上报——这类库的"上游测试"
只能定为官方 demo。

## 根因

- 学术数值库常见形态：作者以 demo（demo-c.c，Vegas/Suave/Divonne/Cuhre
  四算法跑同一被积函数）+ 论文基准做验证，不维护自动化测试。
- demo-c.c 依赖 `-DREALSIZE=8`（makefile 由 configure 注入）才走
  `#include "cuba.h"` 默认分支；10/16 分支需 sed 生成 cubal.h/cubaq.h。

## 解决方案

1. **demo 作 L1 smoke**：build() 内 `-DREALSIZE=8 -I<src>` 编译 demo-c.c
   链 libcuba.a 实跑；判据 = exit 0 + 输出含 4 个算法节标题
   （"Vegas test"…"Cuhre test" grep 齐全性）。body/MANIFEST 如实写
   "上游无正式测试套件，N=4 demo 判定点"。
2. **数值正确性下沉 test_package**：蒙特卡洛算法有随机性不宜断言数值，
   选**确定性** Cuhre 积分常数函数 f=1 于单位立方体 → 精确 1.0（容差
   1e-9）作鸿蒙特有断言。
3. 只编 `make lib`：`make all` 还要 Mathematica `mcc`/fortran 前端工具，
   与本目标无关。
4. configure 显式 `--build/--host=aarch64-unknown-linux-gnu`（老 config.guess
   写盘探针 HMFS 被拒的同款规避，复用 libmatheval 条目）。

## 禁止策略

- 不得把 demo 运行包装成"上游测试套件通过"——如实写"无正式套件 + demo smoke"。
- 不得对 Vegas/Suave（蒙特卡洛，默认种子下跨 libc 亦可能有差异）做数值断言，
  数值断言只用于确定性算法（Cuhre/Divonne 的确定性路径）。
- 不得跑 `make all`（引入 Mathematica/fortran 无谓失败面）。

## 适用范围

无自动化测试套件、以 demo/example 为验证载体的学术数值库
（Cuba/随机数/特殊函数族常见）。
