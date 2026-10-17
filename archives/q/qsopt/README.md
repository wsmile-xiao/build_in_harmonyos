# QSopt_ex（qsopt）

精确有理数线性规划（LP）求解器库。QSopt_ex 在 QSopt 的单纯形算法之上使用
GMP 有理数做精确算术，给出**精确**最优解（而非浮点近似），适用于需要可验证
最优性的场景（组合优化、整数规划预求解、教学与验证）。

- 上游: https://github.com/jonls/qsopt-ex（tag v2.5.10.3）
- 许可证: GPL-3.0-or-later
- 构建系统: autotools
- 语言: C（C99）

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| [2.5.10.3](./2.5.10.3/) | built | 2026-09-27 |

## 库用法

包提供静态库 `libqsopt_ex.a` 与头文件 `include/qsopt_ex/QSopt_ex.h`（以及
lib_dbl/lib_mpf/lib_mpq 模板头）。典型求解流程：

```c
#include <qsopt_ex/QSopt_ex.h>

QSexactStart();
QSexact_set_precision(128);
mpq_QSprob p = mpq_QSload_prob("name", ncols, nrows, cmatcnt, cmatbeg,
                               cmatind, cmatval, QS_MAX, obj, rhs, sense,
                               lower, upper, colnames, rownames);
QSexact_solver(p, NULL, NULL, NULL, DUAL_SIMPLEX, &status);
mpq_QSget_objval(p, &value);      /* 精确最优值（mpq_t） */
mpq_QSfree_prob(p);
QSexactClear();
```

头文件位于 `include/qsopt_ex/`，编译链接时需同时链接 `-lqsopt_ex -lgmp -lm -lpthread`。

## OHOS 适配要点

- 依赖 gmp/6.3.0（硬依赖）、zlib/1.3.1、bzip2/1.0.8（压缩 LP/MPS 文件 I/O）
- 构建期处理全部 OHOS 兼容点（见 `manifest.yaml` / `notes.md`）：
  autoreconf → config.sub 幂等三元组补丁 → 探针 pin → 依赖 -I/-L 注入
- 默认静态库；需要共享库时 `-o qsopt/*:shared=True`（OHOS 下配方自动注入
  SDK llvm/lib 搜索路径供 libtool 共享探测）

## 测试

- 上游: `make check` 跑 `tests/test_qs` TAP 套件（8 项，与 test_package 同源 LP）
- test_package: 求解上游同款小 LP，断言返回 `QS_LP_OPTIMAL` 且精确最优值
  = 42/1（`./test`）
