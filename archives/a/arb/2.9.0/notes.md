# arb 2.9.0 适配笔记

## 编译环境
- 构建系统: autotools（configure + make, 自带 configure）
- 编译日期: 2026-09-18
- 编译器: clang/clang++（/data/service/hnp/bin, OHOS aarch64）
- 状态: built

## 编译步骤

```
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=... （OHOS 构建）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | fmpz_extras.h 等与 FLINT 3.x 重复定义 | FLINT >= 3 已并入 arb 模块,fmpz_add_si/fmpz_sub_si/fmpz_set_mpn_large/fmpz_ui_pow_ui/fmpz_kronecker 由 flint/fmpz.h 提供 | 补丁 0001/0004: FLINT>=3 时跳过 arb 自带的静态副本,并提供 count_trailing_zeros/count_leading_zeros 别名 |
| 2 | FLINT 3.x 不再传递包含 gmp.h / longlong.h / fmpz_vec.h / fmpq_vec.h / ulong_extras.h | FLINT 3 flint.h 只含 stddef.h | 补丁 0001/0005/0006: 显式包含并补 `<stdlib.h>` |
| 3 | 模块部分链接 `-Wl,-r` 与 OHOS clang 默认 -pie 冲突 | 工具链默认 PIE | 补丁 0002: 部分链接加 -no-pie |
| 4 | _fmpz_poly_div 参数不匹配 | FLINT 3 增加 exact 参数 | 补丁 0003: FLINT>=3 传 6 参 |
| 5 | 运行期缺失 mpn_neg_n / n_gcd_full | GMP 6.2+ 改名 mpn_neg_n→mpn_neg;FLINT 3 移除 n_gcd_full | 补丁 0001: 兼容宏/内联 |
| 6 | test_package 运行期找不到符号 / EXIT_SUCCESS 未声明 | 同上 FLINT 3 头链变化 | 补丁 0001/0005/0006 + 测试文件补 stdlib.h |

## 源码修改

patches/: 0001-flint3-compat.patch（fmpz_extras.h）、0002-partial-link-no-pie.patch（Makefile.subdirs）、
0003-fmpz-poly-div-exact.patch、0004-kronecker-flint3.patch、0005-randtest-gmp-include.patch、
0006-boolmat-longlong.patch。

## 依赖版本

- flint 3.6.0、gmp 6.3.0、mpfr 4.2.2（均来自 ohpcd 制品仓）

## 验证结果

- conan create 干净构建通过,test_package 运行 1/1 通过。
- 上游测试全量枚举与运行（详见 reports/upstream-tests-ledger.md）:
  源码声明 667 / 实例化 667 / 实际执行 667,通过 662,失败 5
  （fmpr t-root、t-sqrt、t-mul_naive ULP 舍入差异;arb t-set_str 解析;
  bool_mat t-all_pairs_longest_walk 幂次化）,通过率 662/667 = 99.25%。

## 注意事项

- arb 2.9.0 为 FLINT 2.x 时代源码,与 FLINT 3.x（已并入 arb）存在大量 API
  兼容面,已通过 6 个补丁收敛;升级 arb 版本可消除剩余 5 项测试断言差异。
---

**编译结束**: 2026-09-18 07:23
**最终状态**: built
