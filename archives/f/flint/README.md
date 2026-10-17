# FLINT (Fast Library for Number Theory)

## 简介
FLINT 是数论计算库，提供任意精度整数（fmpz）、有理数（fmpq）、多项式、矩阵，
以及任意精度实数与复数的**区间**运算（arb/acb，自 FLINT 3 起并入本库）。
底层依赖 GMP 做大整数、MPFR 做高精度浮点。

## 基本信息
- 官网: https://flintlib.org/
- 源码: https://github.com/flintlib/flint/releases
- 许可证: LGPLv3
- 构建系统: autotools
- 依赖: gmp/6.3.0、mpfr/4.2.2

## 已编译版本

| 版本 | soname | 状态 | 日期 |
|---|---|---|---|
| 3.2.2 | `libflint.so.20` | built（真机 conan create + 16 条断言通过） | 2026-08-10 |
| 3.6.0 | `libflint.so.24` | built（真机 conan create + 20 条断言通过） | 2026-08-15 |

> **选版提示**：soname 随版本变，选版须按消费方实际需要的那个 soname 挑 ——
> 3.1.x 是 `libflint.so.19`、3.2.x 是 `.so.20`、3.3.x 是 `.so.21`、
> 3.4.x 是 `.so.22`、3.5.x 是 `.so.23`、3.6.x 是 `.so.24`。
> 3.2.2 是 symengine 所需的 soname；3.6.0 为最新版本升级，
> 新增实根隔离（arb_fmpz_poly_real_roots）与区间最简有理数
> （arb_get_simplest_fmpq）等能力。

## 消费方式

```bash
conan install --requires=flint/3.6.0 -pr ohos-native
# 或部署到 ~/usr/local
conan install --requires=flint/3.6.0 -pr ohos-native --deployer=usr_local
```

头文件用 `<flint/fmpz.h>` 这种形式（头装在 `include/flint/`，
而 `.pc` 的 Cflags 是 `-I${includedir}`）。

## 已知特性

gmp/mpfr 在制品仓是**静态**包，被整体链进 `libflint.so`。因此
`DT_NEEDED` 只剩 `libc.so`（部署自包含），但 libflint.so 同时重导出了
大量 `__gmp*` 与 `mpfr_*` 符号。下游若另外动态链接一份 libgmp，
运行期会有两份 GMP 代码共存（符号插入使先加载者胜出）；默认分配器一致时
通常无害，调用过 `mp_set_memory_functions` 的场景需留意。
